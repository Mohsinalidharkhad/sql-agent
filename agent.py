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
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain.memory import ConversationBufferWindowMemory
# Langsmith tracing imports
try:
    from langsmith import traceable
except ImportError:
    traceable = lambda x=None, **kwargs: (lambda f: f) if x is None else x  # no-op if not installed

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Set Langsmith tracing environment variables if not already set
os.environ.setdefault("LANGSMITH_TRACING", "true")
os.environ.setdefault("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
# Optionally, set LANGSMITH_API_KEY from env if present
if "LANGSMITH_API_KEY" in os.environ:
    os.environ["LANGSMITH_API_KEY"] = os.environ["LANGSMITH_API_KEY"]

def read_schema_from_markdown() -> str:
    """Read and return the database schema from the markdown file."""
    try:
        schema_path = os.path.join(os.path.dirname(__file__), 'db_schema.md')
        with open(schema_path, 'r') as file:
            schema_content = file.read()
            
        # Add 8 spaces of indentation to each line
        indented_content = '\n'.join('        ' + line if line.strip() else line.strip() 
                                   for line in schema_content.splitlines())
        
        logger.info("Successfully read database schema from markdown file")
        return indented_content
    except Exception as e:
        logger.error(f"Failed to read schema file: {str(e)}")
        raise

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    openai_api_key=os.environ.get("OPENAI_API_KEY")
)

# Initialize Pinecone
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = "restaurant-db"
index = pc.Index(index_name)
vector_store = PineconeVectorStore(embedding=embeddings, index=index)

retriever = vector_store.as_retriever(
    search_kwargs={"k": 10},
    # search_type="similarity"
)
description = (
    "Use to look up values to filter on. Input is an approximate spelling "
    "of the proper noun, output is valid proper nouns with their source information. "
    "Use the noun most similar to the search."
)
retriever_tool = create_retriever_tool(
    retriever,
    name="search_proper_nouns",
    description=description,
)

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
        tools.append(retriever_tool)
        logger.info(f"Created tools: {[tool.name for tool in tools]}")

        # Get database schema from markdown
        db_schema = read_schema_from_markdown()

        # Use a simple string buffer for chat history (optional)
        # You can use ConversationBufferMemory if you want to keep history as a string
        from langchain.memory import ConversationBufferMemory
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="input",
            output_key="output"
        )

        template = f"""You are an agent designed to interact with a SQL database.
        Given an input question, create a syntactically correct {{dialect}} query to run, then look at the results of the query and return the answer.
        You can order the results by a relevant column to return the most interesting examples in the database.
        Never query for all the columns from a specific table, only ask for the relevant columns given the question.
        User uses colloquial language to ask questions, so always refer to the Synonym words in the database schema information to understand the user's question first.
        Here is the database schema information:
        {db_schema}


        If Previous conversation history
        If you need to filter on a proper noun like a dish name or ingredient name, or item modifier, or dish variant, you must ALWAYS first look up the filter value in the AI response in the Previous conversation history, if you find that value in the Previous AI response use it else find the exact proper noun using the 'search_proper_nouns' tool! Do not try to guess at the proper name - use this function to find similar ones.
        
        When you do not find an item that user is looking for, present user with the closest match based on the category of the item, is_vegeterian, is_vegan, spicy_level, and cuisine. Just like how restaurant waiter would do.

        You have access to tools for interacting with the database.
        Only use the below tools. Only use the information returned by the below tools to construct your final answer.
        You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.
        DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
        ALWAYS remove backticks from the query before executing it.
        ALWAYS remove the extra quotation marks (if any) at the beginning and end of the query before executing it.

        Use the following format:
        
        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{{tool_names}}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question
        
        Begin!
        
        Previous conversation history (if any):
        {{chat_history}}
        
        Here are the tools you have access to:
        {{tools}}

        Question: {{input}}
        
        {{agent_scratchpad}}"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "dialect", "agent_scratchpad", "chat_history"],
            partial_variables={
                "tool_names": ", ".join([tool.name for tool in tools])
            }
        )
        
        agent = create_react_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=False,
            handle_parsing_errors=True
        )
        
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
            "dialect": dialect
        })
        logger.info(f"Raw agent result: {result}")
        
        if result and "output" in result:
            # Format the response nicely
            response = result["output"]
            # Log intermediate steps for debugging
            if "intermediate_steps" in result:
                logger.debug("Intermediate steps:")
                for step in result["intermediate_steps"]:
                    logger.debug(f"- Action: {step[0]}")
                    logger.debug(f"- Result: {step[1]}\n")
            return response
        else:
            logger.warning("No output in agent result")
            return "I apologize, but I couldn't generate a response. Please try asking about specific tables like 'dishes' or 'menu'."
            
    except Exception as e:
        error_msg = f"Error querying agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

@traceable(name="main")
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
