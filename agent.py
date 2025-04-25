import os
from typing import List, Tuple
import logging

from dotenv import load_dotenv
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.agents import AgentExecutor, create_react_agent
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.prompts import MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

def get_supabase_connection_string() -> str:
    """Get Supabase connection string from environment variables."""
    host = os.getenv("SUPABASE_HOST")
    database = os.getenv("SUPABASE_DATABASE", "postgres")
    user = os.getenv("SUPABASE_USER", "postgres")
    password = os.getenv("SUPABASE_PASSWORD")
    port = os.getenv("SUPABASE_PORT", "5432")
    
    # Log environment variable status (without sensitive info)
    logger.info(f"Database configuration - Host: {host}, Database: {database}, User: {user}, Port: {port}")
    if not host or not password:
        logger.error("Missing required environment variables (SUPABASE_HOST or SUPABASE_PASSWORD)")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

def create_sql_database() -> SQLDatabase:
    """Create SQLDatabase instance connected to Supabase."""
    try:
        logger.info("Attempting to create database connection...")
        connection_string = get_supabase_connection_string()
        db = SQLDatabase.from_uri(connection_string)
        logger.info("Database connection successful")
        
        # Log available tables
        tables = db.get_usable_table_names()
        logger.info(f"Available tables in database: {tables}")
        
        return db
    except Exception as e:
        logger.error(f"Failed to create database connection: {str(e)}")
        raise

def setup_agent(db: SQLDatabase) -> AgentExecutor:
    """Set up the SQL agent with the database."""
    try:
        logger.info("Setting up SQL agent...")
        llm = init_chat_model("openai:gpt-4o-mini", temperature=0)
        logger.info("LLM initialized successfully")
        
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        tools = toolkit.get_tools()
        logger.info(f"Created tools: {[tool.name for tool in tools]}")

        template = """You are an agent designed to interact with a SQL database.
        Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
        You can order the results by a relevant column to return the most interesting examples in the database.
        Never query for all the columns from a specific table, only ask for the relevant columns given the question.

        You have access to tools for interacting with the database.
        Only use the below tools. Only use the information returned by the below tools to construct your final answer.
        You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.
        DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

        To start you should ALWAYS look at the tables in the database to see what you can query.
        Do NOT skip this step.
        Then you should query the schema of the most relevant tables.

        Available tools: {tool_names}
        
        {tools}
        
        Use the following format:
        
        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question
        
        Begin!
        
        Question: {input}
        
        {agent_scratchpad}"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "dialect", "agent_scratchpad"],
            partial_variables={
                "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in tools]),
                "tool_names": ", ".join([tool.name for tool in tools])
            }
        )
        
        agent = create_react_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        
        logger.info("Agent executor created successfully")
        return agent_executor
        
    except Exception as e:
        logger.error(f"Failed to set up agent: {str(e)}")
        raise

def query_agent(agent: AgentExecutor, query: str) -> str:
    """Query the SQL agent with a natural language question."""
    try:
        logger.info(f"Processing query: {query}")
        # Execute the agent with the query
        result = agent.invoke({
            "input": query,
            "dialect": dialect  # Pass the dialect variable
        })
        logger.info(f"Raw agent result: {result}")
        
        if result and "output" in result:
            return result["output"]
        else:
            logger.warning("No output in agent result")
            return "I apologize, but I couldn't generate a response. Please try asking about specific tables like 'dishes' or 'menu'."
            
    except Exception as e:
        error_msg = f"Error querying agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

def main():
    try:
        logger.info("Starting the application...")
        # Initialize database connection
        db = create_sql_database()
        global dialect 
        dialect = db.dialect
        logger.info(f"Database dialect set to: {dialect}")
        
        # Create agent
        agent = setup_agent(db)
        logger.info("Agent setup completed")
        
        # Example usage
        while True:
            question = input("\nEnter your question (or 'quit' to exit): ")
            if question.lower() == 'quit':
                logger.info("User requested to quit")
                break
                
            response = query_agent(agent, question)
            print(f"\nResponse: {response}")
            
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
