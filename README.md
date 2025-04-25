# SQL Agent with LangChain and Supabase

This project implements a natural language to SQL agent using LangChain and Supabase as the database backend. It uses GPT-4-turbo for natural language processing and SQL generation.

## Features

- Natural language to SQL conversion using GPT-4o-mini
- Direct integration with Supabase database
- Error handling and user-friendly responses
- Interactive command-line interface
- Secure credential management
- Type-safe database operations

## Requirements

- Python 3.8+
- OpenAI API key
- Supabase project with database access
- Sufficient permissions to read from database tables

## Setup

1. Clone this repository

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your credentials:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   SUPABASE_HOST=your_supabase_host
   SUPABASE_DATABASE=postgres
   SUPABASE_USER=postgres
   SUPABASE_PASSWORD=your_supabase_db_password
   SUPABASE_PORT=5432
   ```

5. Replace the placeholder values in `.env` with your actual credentials:
   - Get your OpenAI API key from: https://platform.openai.com/api-keys
   - Get your Supabase credentials from your project's Database Settings

## Usage

1. Run the agent:
   ```bash
   python agent.py
   ```

2. Enter your questions in natural language. The agent will:
   - Convert your question to SQL using GPT-4-turbo
   - Validate the generated SQL for safety
   - Execute the query against your Supabase database
   - Return the results in a human-readable format

3. Type 'quit' to exit the program

## Example Questions

You can ask questions like:
- "How many users are in the database?"
- "What are the top 5 most recent orders?"
- "Show me all customers who made purchases last month"
- "What's the average order value per customer?"
- "List all products with low inventory"

## Safety Notes

- The agent uses read-only operations by default
- All SQL queries are validated before execution
- Sensitive data is never logged or exposed
- Database credentials are securely managed through environment variables

## Troubleshooting

If you encounter any issues:
1. Ensure all environment variables are correctly set
2. Verify your OpenAI API key has sufficient credits
3. Check your Supabase database connection and permissions
4. Make sure all dependencies are installed correctly

## Dependencies

See `requirements.txt` for a complete list of dependencies and their versions. 