from unittest.mock import patch, MagicMock
from open_data_scientist.codeagent import ReActDataScienceAgent
from open_data_scientist.utils.executors import delete_session_internal


def test_session_cleanup_on_agent_deletion():
    """Test that session is automatically cleaned up when agent object is deleted."""
    
    # Here i need to mock the llm response so at least for this time we do not need to call 
    # any llm (this """"""should""""" be fine as we have other tests for that)
    mock_response = """<think>
I need to execute some Python code to test the session creation.
</think>
<code>
```python
print('hello world')
x = 42
print(f'x = {x}')
```
</code>"""
    
    with patch('open_data_scientist.codeagent.create_llm_provider') as mock_create_provider:
        # Configure the mock provider
        mock_provider = MagicMock()
        mock_create_provider.return_value = mock_provider
        mock_provider.generate.return_value = mock_response
        
        # Create agent and run a task to generate a session
        agent = ReActDataScienceAgent(executor="internal", max_iterations=1)
        
        # Run the task - this should execute the mocked code and create a session
        _ = agent.run("test task")
        
        # Store the session ID
        session_id = agent.session_id
        assert session_id is not None
        
        # Delete the agent object to trigger cleanup
        del agent
        
        # Verify session was cleaned up by trying to delete it manually
        # This should fail because the session was already deleted by the destructor
        delete_result = delete_session_internal(session_id)
        assert delete_result["success"] is False
        assert "error" in delete_result
        
        # Test calling deletion twice - second call should also fail
        delete_result2 = delete_session_internal(session_id)
        assert delete_result2["success"] is False
        assert "error" in delete_result2 
