# Import necessary libraries
import os
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

# Load the .env file
load_dotenv()

# Access environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Step 1: Embed Markdown Notes Directory
def load_and_embed_markdown(directory_path):
    """
    Recursively loads markdown files from a directory (including subdirectories)
    and embeds them into a FAISS vectorstore.
    """
    docs = []
    for root, _, files in os.walk(directory_path):
        for filename in files:
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                loader = TextLoader(filepath)
                try:
                    docs.extend(loader.load())
                except Exception as e:
                    print(f"Error loading file {filepath}: {e}")

    if not docs:
        raise ValueError("No markdown files were found. Ensure the directory contains valid .md files.")

    # Embed documents using OpenAI embeddings
    embeddings = OpenAIEmbeddings()
    try:
        vectorstore = FAISS.from_documents(docs, embeddings)
    except Exception as e:
        print(f"Error creating vectorstore: {e}")
        raise

    return vectorstore

# Step 2: Define Custom Prompt Templates
system_template = """The files returned in this rag pipeline are markdown files from an obsidian template. 
Items are formatted in a to do list. For example:
    -[ ] means that a task need to be done
    -[x] means that the task has been completed. 
    
When asking about to do items, please ignore completed tasks, and only return uncompleted tasks.  
----------------
{context}"""
human_template = "{question}"

# Create message prompt templates
system_message = SystemMessagePromptTemplate.from_template(system_template)
human_message = HumanMessagePromptTemplate.from_template(human_template)

# Combine system and human messages into a chat prompt template
chat_prompt = ChatPromptTemplate.from_messages([system_message, human_message])

# Step 3: Setup Retrieval-augmented QA Chain
def setup_rag_chain(vectorstore, api_key=OPENAI_API_KEY):
    """
    Sets up a retrieval-augmented QA (RAG) chain for querying.
    :param vectorstore: The FAISS vectorstore containing embedded documents.
    :param api_key: API key for OpenAI (if using API-based querying).
    """
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})

    # Define the LLM for retrieval-based QA
    llm = ChatOpenAI(temperature=0, openai_api_key=api_key)

    # Create a RetrievalQA chain (updated approach)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",  # Chain type for combining documents
        retriever=retriever,
        return_source_documents=True,  # Keep source documents for context
        chain_type_kwargs={"prompt": chat_prompt}
    )

    return qa_chain

def format_response(response):
    """
    Formats the output of the RAG chain into a readable format.
    :param response: The raw response from the chain.
    :return: A string with only the AI response.
    """
    return f"Response: {response['result']}\n"


# Step 4: Format the Response
# def format_response(response):
#     """
#     Formats the output of the RAG chain into a readable format.
#     :param response: The raw response from the chain.
#     :return: A string with formatted output.
#     """
#     formatted_output = []
#     formatted_output.append(f"Query: {response['query']}\n")
#     formatted_output.append(f"Response: {response['result']}\n")
#
#     # Include reduced context from source documents
#     formatted_output.append("\nRelevant Context:")
#     for i, doc in enumerate(response.get("source_documents", []), 1):
#         file_name = os.path.basename(doc.metadata.get("source", "Unknown File"))
#         content = doc.page_content.strip()
#         truncated_content = content[:200] + ("..." if len(content) > 200 else "")  # Limit to 200 characters
#         formatted_output.append(f"{i}. **File:** {file_name}\n   **Snippet:** {truncated_content}\n")
#
#     return "\n".join(formatted_output)
#

# Step 5: Execute a Query
def execute_query(chain, query):
    """
    Executes a query against the RAG chain and returns the response.
    :param chain: The RAG chain for querying.
    :param query: The user query.
    :return: The formatted response generated by the chain.
    """
    try:
        response = chain.invoke({"query": query})
        return format_response(response)
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

# Main Script
if __name__ == "__main__":
    # Path to the directory with markdown notes
    markdown_directory = input("Path to your Obsidian Vault or Markdown Directory: ")

    # Step 1: Load and embed markdown files
    print("Embedding markdown notes...")
    try:
        vectorstore = load_and_embed_markdown(markdown_directory)
    except Exception as e:
        print(f"Failed to embed markdown notes: {e}")
        exit(1)

    # Step 2: Set up the RAG chain
    print("Setting up retrieval-augmented QA (RAG)...")
    try:
        rag_chain = setup_rag_chain(vectorstore, OPENAI_API_KEY)
    except Exception as e:
        print(f"Failed to set up RAG chain: {e}")
        exit(1)

    # Step 3: Query the chain
    print("Ready to query your notes! Type 'exit' or 'quit' to stop.")
    while True:
        query = input("Enter your query: ")
        if query.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        response = execute_query(rag_chain, query)
        if response:
            print(response)
