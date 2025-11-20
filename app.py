import streamlit as st
import pandas as pd
from utils import fetch_workflows_generator, process_workflows

# Page Configuration
st.set_page_config(
    page_title="n8n Model Usage Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
    <style>
    .main {
        /* background-color: #f8f9fa;  Removed to let Streamlit theme control background */
    }
    .stMetric {
        background-color: #262730; /* Darker background for cards */
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #464b5d;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        min-height: 130px; /* Enforce uniform height */
        display: flex;
        flex-direction: column;
        justify_content: center;
    }
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    h1, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        /* Removed specific color to adapt to theme */
    }
    </style>
    """, unsafe_allow_html=True)

# Title and Description
st.title("📊 n8n Workflow Model Tracker")
st.markdown("Monitor and manage chat model usage across your n8n workflows. Identify workflows using OpenRouter vs. other providers.")

# Sidebar for Actions
with st.sidebar:
    st.header("Configuration")
    base_url_input = st.text_input("N8N Base URL", help="Enter your n8n Base URL (e.g., https://n8n.example.com).")
    api_key_input = st.text_input("N8N API Key", type="password", help="Enter your n8n API key here.")
    batch_size_input = st.number_input("Batch Size", min_value=1, max_value=250, value=10, help="Number of workflows to fetch per API call.")
    
    st.header("Controls")
    fetch_btn = st.button("Fetch Workflows", type="primary")
    
    if st.button("Refresh Data"):
        st.session_state.workflow_data = None # Clear session state to force re-fetch
        st.rerun()
    
    st.markdown("---")
    st.markdown("### About")
    st.info("This dashboard helps track the adoption of OpenRouter across the team's workflows.")

# Initialize session state for data
if "workflow_data" not in st.session_state:
    st.session_state.workflow_data = None

# Helper function to render the dashboard content
def render_dashboard(openrouter_list, other_list, all_list):
    # Metrics Section
    col1, col2, col3 = st.columns(3)
    
    total_workflows = len(all_list)
    openrouter_count = len(openrouter_list)
    other_model_count = len(other_list)
    
    openrouter_pct = (openrouter_count / total_workflows * 100) if total_workflows > 0 else 0
    
    with col1:
        st.metric(
            label="Total Workflows", 
            value=total_workflows,
            delta="All active & inactive",
            delta_color="off"
        )
        
    with col2:
        st.metric(
            label="Using OpenRouter", 
            value=openrouter_count,
            delta=f"{openrouter_pct:.1f}%",
            delta_color="normal"
        )
        
    with col3:
        st.metric(
            label="Using Other Models", 
            value=other_model_count,
            delta=f"{other_model_count} workflows",
            delta_color="off"
        )

    # Tabs for detailed views
    tab1, tab2, tab3 = st.tabs(["🚀 OpenRouter Workflows", "⚠️ Other Model Workflows", "📋 All Workflows"])
    
    # Configure columns for better display
    column_config = {
        "ID": st.column_config.TextColumn("Workflow ID", help="Unique identifier"),
        "Name": st.column_config.TextColumn("Workflow Name", width="medium"),
        "Active": st.column_config.CheckboxColumn("Active Status"),
        "Chat Model Used": st.column_config.TextColumn("Chat Model", width="medium"),
        "Key": st.column_config.TextColumn("Key Name", width="medium"),
        "Model Used": st.column_config.TextColumn("Model (OpenRouter)", width="medium"),
    }

    # Helper to calculate dynamic height
    def get_table_height(df):
        # Header (35px) + Rows (35px each) + Buffer
        # Min height 150px to show empty state or few rows nicely
        return max(150, (len(df) + 1) * 35 + 3)

    with tab1:
        st.subheader("Workflows using OpenRouter")
        st.markdown("These workflows are correctly using the OpenRouter integration.")
        if openrouter_list:
            df_openrouter = pd.DataFrame(openrouter_list)
            st.dataframe(
                df_openrouter,
                column_config=column_config,
                hide_index=True,
                width='stretch',
                key="openrouter_table",
                height=get_table_height(df_openrouter)
            )
        else:
            st.info("No workflows found for this category.")

    with tab2:
        st.subheader("Workflows using Other Models")
        st.markdown("These workflows are using other chat models (e.g., OpenAI, Gemini). **Consider migrating to OpenRouter.**")
        if other_list:
            df_other = pd.DataFrame(other_list)
            st.dataframe(
                df_other,
                column_config=column_config,
                hide_index=True,
                width='stretch',
                key="other_table",
                height=get_table_height(df_other)
            )
        else:
            st.success("Great job! No workflows are using other models.")

    with tab3:
        st.subheader("All Workflows")
        if all_list:
            df_all = pd.DataFrame(all_list)
            st.dataframe(
                df_all,
                column_config=column_config,
                hide_index=True,
                width='stretch',
                key="all_table",
                height=get_table_height(df_all)
            )
        else:
            st.info("No workflows found.")

# Main Logic
if api_key_input:
    # Check if we need to fetch data (fetch button clicked)
    if fetch_btn:
        
        # Containers for live updates
        status_container = st.empty()
        dashboard_placeholder = st.empty()
        
        all_workflows_dict = {} # Deduplication dictionary
        
        with status_container.status("Fetching workflows...", expanded=True) as status:
            
            # Construct API URL
            api_url = None
            if base_url_input:
                # Remove trailing slash if present to avoid double slashes
                base_url_clean = base_url_input.rstrip('/')
                api_url = f"{base_url_clean}/api/v1/workflows"

            # Generator loop
            for batch in fetch_workflows_generator(api_url=api_url, api_key=api_key_input, batch_size=batch_size_input):
                
                if isinstance(batch, dict) and "error" in batch:
                    status.error(batch["error"])
                    st.stop()
                
                # Deduplicate and accumulate
                for wf in batch:
                    wf_id = wf.get("id")
                    if wf_id:
                        all_workflows_dict[wf_id] = wf
                
                all_workflows_accumulated = list(all_workflows_dict.values())
                
                # Update status message
                status.write(f"Fetched {len(all_workflows_accumulated)} workflows...")
                
                # Process current accumulated data
                openrouter_list, other_list, all_list = process_workflows({"data": all_workflows_accumulated})
                
                # Update Dashboard Live
                with dashboard_placeholder.container():
                    render_dashboard(openrouter_list, other_list, all_list)
            
            status.update(label="Workflows fetched successfully!", state="complete", expanded=False)
        
        # Store final data in session state
        st.session_state.workflow_data = {
            "openrouter": openrouter_list,
            "other": other_list,
            "all": all_list
        }
        
    elif st.session_state.workflow_data:
        # Render from session state if available
        data = st.session_state.workflow_data
        render_dashboard(data["openrouter"], data["other"], data["all"])

else:
    st.warning("Please enter your N8N details and click on Fetch Workflows button in the sidebar to view the dashboard.")
