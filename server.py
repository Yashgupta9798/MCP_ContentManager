from agent.agent import Agent


def main():
    print("===== CM AI SERVER STARTED =====")

    agent = Agent()

    while True:
        user_query = input("\nEnter your query (type 'exit' to stop): ")

        if user_query.lower() == "exit":
            print("Server stopped.")
            break

        print("\n--- Sending query to Agent ---")

        response = agent.handle_query(user_query)

        print("\n--- Final Response Stored in Variable 'response' ---")
        print(response)


if __name__ == "__main__":
    main()
