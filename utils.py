import requests
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_workflows_generator(api_url=None, api_key=None):
    """
    Generator that yields batches of workflows from the n8n API using pagination.
    """
    if not api_key:
        api_key = os.getenv("N8N_API_KEY")
    
    if not api_url:
        base_url = os.getenv("N8N_BASE_URL")
        if base_url:
            api_url = f"{base_url}/api/v1/workflows"
    
    if not api_key:
        yield {"error": "API key not found. Please set N8N_API_KEY in .env file."}
        return
        
    if not api_url:
        yield {"error": "API URL not found. Please set N8N_BASE_URL in .env file or pass api_url."}
        return

    headers = {
        'X-N8N-API-KEY': api_key
    }

    cursor = None
    
    try:
        # Get batch size from env, default to 20
        batch_size = int(os.getenv("N8N_BATCH_SIZE", 20))
        
        while True:
            params = {'limit': batch_size}
            if cursor:
                params['cursor'] = cursor
            
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            workflows = data.get("data", [])
            yield workflows
            
            cursor = data.get("nextCursor")
            
            if not cursor:
                break

    except ValueError as e: # Includes JSONDecodeError
        content = response.text[:500] if 'response' in locals() and response else "No response content"
        status = response.status_code if 'response' in locals() and response else "Unknown"
        yield {"error": f"Failed to decode JSON. Status: {status}, URL: {api_url}, Content: {content}..."}
    except requests.exceptions.RequestException as e:
        yield {"error": f"Request failed: {e}"}
    except Exception as e:
        yield {"error": f"An unexpected error occurred: {e}"}

def process_workflows(data):
    """
    Processes the workflow data to categorize them by model usage.
    """
    if "error" in data:
        return [], [], []

    workflows = data.get("data", [])
    
    openrouter_workflows = []
    other_model_workflows = []
    all_workflows_data = []

    for workflow in workflows:
        workflow_name = workflow.get("name", "Unnamed Workflow")
        workflow_id = workflow.get("id")
        nodes = workflow.get("nodes", [])
        
        has_openrouter = False
        has_other_model = False
        
        chat_models = []
        keys = []
        models = []

        for node in nodes:
            node_type = node.get("type")
            node_name = node.get("name")
            
            is_openrouter = node_type == "@n8n/n8n-nodes-langchain.lmChatOpenRouter"
            is_other_chat = "lmChat" in node_type or "ChatModel" in node_name
            
            if is_openrouter or is_other_chat:
                if is_openrouter:
                    has_openrouter = True
                else:
                    has_other_model = True
                
                # 1. Chat Model Used
                chat_models.append(node_name)
                
                # 2. Key (Credentials)
                credentials = node.get("credentials", {})
                for cred_val in credentials.values():
                    if isinstance(cred_val, dict) and "name" in cred_val:
                        keys.append(cred_val["name"])
                
                # 3. Model Used (Only for OpenRouter)
                if is_openrouter:
                    model_val = node.get("parameters", {}).get("model")
                    if model_val:
                        if isinstance(model_val, dict):
                             models.append("Dynamic")
                        else:
                             models.append(str(model_val))

        workflow_info = {
            "ID": workflow_id,
            "Name": workflow_name,
            "Active": workflow.get("active", False),
            "Chat Model Used": ", ".join(chat_models) if chat_models else "None",
            "Key": ", ".join(keys) if keys else "None",
            "Model Used": ", ".join(models) if models else ""
        }
        
        all_workflows_data.append(workflow_info)

        if has_openrouter:
            openrouter_workflows.append(workflow_info)
        
        if has_other_model:
            other_model_workflows.append(workflow_info)
            
    return openrouter_workflows, other_model_workflows, all_workflows_data
