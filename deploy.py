"""
Deploy any agent from the agents/ folder to Vertex AI Agent Engine.

Usage:
    python deploy.py --agent VeloceAgent --create
    python deploy.py --agent baseLawAgent --create
    python deploy.py --list
    python deploy.py --delete --resource_id <id>
    python deploy.py --agent VeloceAgent --send --resource_id <id> --session_id <id> --message "Hello"
"""

import argparse
import importlib
import os
import sys

import vertexai
from dotenv import dotenv_values, load_dotenv
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

AGENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents")

# Base requirements every agent needs on Vertex AI
BASE_REQUIREMENTS = [
    "google-cloud-aiplatform[adk,agent_engines]",
    "google-adk",
    "python-dotenv",
    "google-auth",
]

# Per-agent extra pip requirements (add entries as you create new agents)
AGENT_REQUIREMENTS = {
    "VeloceAgent": ["requests", "openpyxl", "google-cloud-storage"],
    "baseLawAgent": ["llama-index"],
}

# Env vars to forward to the deployed agent (beyond GCP project/location which
# Vertex AI sets automatically).  Add keys here as new agents need them.
DEPLOY_ENV_VARS = [
    "GOOGLE_GENAI_USE_VERTEXAI",
    "VERTEX_AI_MODEL",
    "KNOWLEDGE_RAG_CORPUS",
    "DRAFTING_RAG_CORPUS",
    "RESEARCH_RAG_CORPUS",
]


def discover_agents():
    """Find all agent packages under agents/ that have an agent.py with root_agent."""
    agents = []
    if not os.path.isdir(AGENTS_DIR):
        return agents
    for name in sorted(os.listdir(AGENTS_DIR)):
        agent_file = os.path.join(AGENTS_DIR, name, "agent.py")
        if os.path.isfile(agent_file):
            agents.append(name)
    return agents


def load_agent(agent_name: str):
    """Dynamically import and return root_agent from agents/<agent_name>/agent.py."""
    # Add agents/ to sys.path so the package can be imported
    if AGENTS_DIR not in sys.path:
        sys.path.insert(0, AGENTS_DIR)

    try:
        module = importlib.import_module(f"{agent_name}.agent")
    except ModuleNotFoundError as e:
        available = discover_agents()
        print(f"Error: Could not import agent '{agent_name}': {e}")
        print(f"Available agents: {', '.join(available) if available else 'none found'}")
        sys.exit(1)

    agent = getattr(module, "root_agent", None)
    if agent is None:
        print(f"Error: {agent_name}/agent.py does not export 'root_agent'")
        sys.exit(1)

    return agent


def get_requirements(agent_name: str) -> list:
    """Build the full pip requirements list for an agent."""
    extra = AGENT_REQUIREMENTS.get(agent_name, [])
    return BASE_REQUIREMENTS + extra


def cmd_create(args):
    agent_name = args.agent
    if not agent_name:
        print("Error: --agent is required for --create")
        sys.exit(1)

    root_agent = load_agent(agent_name)
    requirements = get_requirements(agent_name)

    # Collect env vars to forward to the deployed agent
    env_vars = {k: os.environ[k] for k in DEPLOY_ENV_VARS if k in os.environ}

    print(f"Deploying '{agent_name}' to Vertex AI Agent Engine...")
    print(f"  Requirements: {requirements}")
    print(f"  Env vars: {list(env_vars.keys())}")

    adk_app = AdkApp(agent=root_agent, enable_tracing=True)

    # Change to agents/ dir so extra_packages uses a relative path.
    # The SDK tars the directory as-is, so absolute paths on Windows
    # produce broken paths on the remote Linux container.
    original_cwd = os.getcwd()
    os.chdir(AGENTS_DIR)

    try:
        remote_app = agent_engines.create(
            agent_engine=adk_app,
            requirements=requirements,
            extra_packages=[f"./{agent_name}"],
            env_vars=env_vars,
        )
    finally:
        os.chdir(original_cwd)

    print(f"\nDeployed successfully!")
    print(f"Agent: {agent_name}")
    print(f"Resource ID: {remote_app.resource_name}")


def cmd_delete(args):
    if not args.resource_id:
        print("Error: --resource_id required for --delete")
        sys.exit(1)

    print(f"Deleting agent: {args.resource_id}")
    agent_engines.delete(args.resource_id)
    print("Deleted successfully!")


def cmd_list(args):
    print("Deployed agents:")
    for agent in agent_engines.list():
        print(f"  {agent.resource_name}")


def cmd_create_session(args):
    if not args.resource_id:
        print("Error: --resource_id required")
        sys.exit(1)

    remote_app = agent_engines.get(args.resource_id)
    session = remote_app.create_session(user_id=args.user_id, state={})
    print(f"Session created!")
    print(f"  Session ID: {session['id']}")


def cmd_list_sessions(args):
    if not args.resource_id:
        print("Error: --resource_id required")
        sys.exit(1)

    remote_app = agent_engines.get(args.resource_id)
    sessions = remote_app.list_sessions(user_id=args.user_id)
    print(f"Sessions for user '{args.user_id}':")
    for session in sessions:
        print(f"  {session['id']}")


def cmd_get_session(args):
    if not args.resource_id or not args.session_id:
        print("Error: --resource_id and --session_id required")
        sys.exit(1)

    remote_app = agent_engines.get(args.resource_id)
    session = remote_app.get_session(user_id=args.user_id, session_id=args.session_id)
    print(f"Session ID: {session['id']}")
    print(f"User ID: {session['user_id']}")
    print(f"State: {session.get('state', {})}")


def cmd_send(args):
    if not args.resource_id or not args.session_id:
        print("Error: --resource_id and --session_id required")
        sys.exit(1)

    remote_app = agent_engines.get(args.resource_id)
    print(f"\nYou: {args.message}")
    print("\nAgent:")

    for event in remote_app.stream_query(
        user_id=args.user_id,
        session_id=args.session_id,
        message=args.message,
    ):
        if event.get("content"):
            for part in event["content"].get("parts", []):
                if "text" in part:
                    print(part["text"])


def main():
    load_dotenv(os.path.join(AGENTS_DIR, ".env"))

    available_agents = discover_agents()

    parser = argparse.ArgumentParser(
        description="Deploy and manage agents on Vertex AI Agent Engine.",
        epilog=f"Available agents: {', '.join(available_agents)}" if available_agents else None,
    )
    parser.add_argument("--agent", choices=available_agents, help="Agent to deploy (folder name under agents/)")
    parser.add_argument("--project_id", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", default=os.getenv("GOOGLE_CLOUD_LOCATION"))
    parser.add_argument("--bucket", default=os.getenv("GOOGLE_CLOUD_STAGING_BUCKET"))
    parser.add_argument("--resource_id", help="Deployed agent resource ID")
    parser.add_argument("--user_id", default="test_user")
    parser.add_argument("--session_id")
    parser.add_argument("--message", default="Hello")

    # Operations (mutually exclusive)
    ops = parser.add_mutually_exclusive_group(required=True)
    ops.add_argument("--create", action="store_true", help="Deploy an agent")
    ops.add_argument("--delete", action="store_true", help="Delete a deployment")
    ops.add_argument("--list", action="store_true", help="List all deployments")
    ops.add_argument("--create_session", action="store_true", help="Create a session")
    ops.add_argument("--list_sessions", action="store_true", help="List sessions for a user")
    ops.add_argument("--get_session", action="store_true", help="Get session details")
    ops.add_argument("--send", action="store_true", help="Send a message to the agent")

    args = parser.parse_args()

    if not args.project_id:
        print("Error: Missing project_id. Use --project_id or set GOOGLE_CLOUD_PROJECT.")
        sys.exit(1)
    if not args.location:
        print("Error: Missing location. Use --location or set GOOGLE_CLOUD_LOCATION.")
        sys.exit(1)

    # Initialize Vertex AI once
    vertexai.init(
        project=args.project_id,
        location=args.location,
        staging_bucket=args.bucket,
    )

    if args.create:
        cmd_create(args)
    elif args.delete:
        cmd_delete(args)
    elif args.list:
        cmd_list(args)
    elif args.create_session:
        cmd_create_session(args)
    elif args.list_sessions:
        cmd_list_sessions(args)
    elif args.get_session:
        cmd_get_session(args)
    elif args.send:
        cmd_send(args)


if __name__ == "__main__":
    main()
