from agent.agent import Agent
from tools.search import search_records
import asyncio


def main():
    print("===== CM AI SERVER STARTED =====")

    agent = Agent()

    while True:
        user_query = input("\nEnter your query (type 'exit' to stop): ")

        if user_query.lower() == "exit":
            print("Server stopped.")
            break

        print("\n--- Sending query to Agent ---")

        # Run the asynchronous handle_query method
        response = asyncio.run(agent.handle_query(user_query))

        print("\n--- Final Response Stored in Variable 'response' ---")
        print(response)


if __name__ == "__main__":
    main()
