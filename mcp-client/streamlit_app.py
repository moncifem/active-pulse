import streamlit as st
import asyncio
from client import MCPClient
import sys
from typing import Optional

class StreamlitMCPApp:
    def __init__(self):
        self.client: Optional[MCPClient] = None
        
    async def initialize_client(self, server_path: str):
        """Initialize the MCP client and connect to server"""
        self.client = MCPClient()
        await self.client.connect_to_server(server_path)
        
    async def process_message(self, message: str) -> str:
        """Process a message through the MCP client"""
        if not self.client:
            return "Error: Client not initialized"
        return await self.client.process_query(message)

def main():
    st.title("MCP Chat Interface")
    
    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Server path input
    server_path = st.text_input("Enter server script path (.py or .js):", "path/to/your/server.py")
    
    # Initialize button
    if st.button("Initialize Client"):
        app = StreamlitMCPApp()
        st.session_state.app = app
        
        # Run initialization
        asyncio.run(app.initialize_client(server_path))
        st.success("Client initialized successfully!")
    
    # Chat interface
    if "app" in st.session_state:
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("What would you like to ask?"):
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Get bot response
            with st.chat_message("assistant"):
                response = asyncio.run(st.session_state.app.process_message(prompt))
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main() 
