from pathlib import Path
from opendata.agents.fixed_agent import ProjectAnalysisAgent
import pytest

def test_start_analysis_with_callback(tmp_path):
    # Create a dummy project
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "data.txt").write_text("some data")
    
    agent = ProjectAnalysisAgent(tmp_path / "workspace")
    progress_msgs = []
    
    def callback(msg):
        progress_msgs.append(msg)
        
    agent.start_analysis(project_dir, progress_callback=callback)
    
    assert len(progress_msgs) > 0
    assert any("Scanning" in m for m in progress_msgs)
    assert any("Checking" in m for m in progress_msgs)
