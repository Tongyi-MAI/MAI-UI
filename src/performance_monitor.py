# Copyright (c) 2025, Alibaba Cloud and its affiliates;
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Performance Monitoring Module for MAI-UI Agents.

This module provides real-time performance tracking and metrics collection
for GUI agents, including execution time, success rates, and step efficiency.
"""

import time
import json
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


@dataclass
class PerformanceMetrics:
    """Container for agent performance metrics."""
    
    task_id: str
    task_goal: str
    total_steps: int = 0
    total_time: float = 0.0
    step_times: List[float] = field(default_factory=list)
    success: bool = False
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_average_step_time(self) -> float:
        """Calculate average time per step."""
        if not self.step_times:
            return 0.0
        return sum(self.step_times) / len(self.step_times)
    
    def get_step_efficiency(self) -> float:
        """Calculate efficiency score (lower is better)."""
        if self.total_time == 0:
            return 0.0
        return self.total_steps / self.total_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        data = asdict(self)
        data['average_step_time'] = self.get_average_step_time()
        data['step_efficiency'] = self.get_step_efficiency()
        return data


class PerformanceMonitor:
    """
    Monitor and track agent performance metrics in real-time.
    
    Provides functionality to track execution time, step count, and success metrics
    for GUI agents.
    """
    
    def __init__(self, task_id: str, task_goal: str, metrics_dir: Optional[str] = None):
        """
        Initialize the performance monitor.
        
        Args:
            task_id: Unique identifier for the task
            task_goal: Description of the task goal
            metrics_dir: Optional directory to save metrics logs
        """
        self.metrics = PerformanceMetrics(task_id=task_id, task_goal=task_goal)
        self.metrics_dir = Path(metrics_dir) if metrics_dir else None
        self._step_start_time: Optional[float] = None
        self._session_start_time = time.time()
        
        if self.metrics_dir:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
    
    def start_step(self) -> None:
        """Mark the start of a new step."""
        self._step_start_time = time.time()
    
    def end_step(self) -> float:
        """
        Mark the end of a step and record its duration.
        
        Returns:
            Duration of the step in seconds
        """
        if self._step_start_time is None:
            raise RuntimeError("step not started, call start_step() first")
        
        step_duration = time.time() - self._step_start_time
        self.metrics.step_times.append(step_duration)
        self.metrics.total_steps += 1
        self._step_start_time = None
        
        return step_duration
    
    def end_task(self, success: bool = True, error: Optional[str] = None) -> None:
        """
        Mark the end of the task and record final metrics.
        
        Args:
            success: Whether the task completed successfully
            error: Optional error message if task failed
        """
        self.metrics.total_time = time.time() - self._session_start_time
        self.metrics.success = success
        self.metrics.error_message = error
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.metrics
    
    def save_metrics(self, filename: Optional[str] = None) -> Optional[Path]:
        """
        Save metrics to a JSON file.
        
        Args:
            filename: Optional custom filename (default: task_id_metrics.json)
            
        Returns:
            Path to saved file, or None if no metrics_dir configured
        """
        if not self.metrics_dir:
            return None
        
        if filename is None:
            filename = f"{self.metrics.task_id}_metrics.json"
        
        filepath = self.metrics_dir / filename
        with open(filepath, 'w') as f:
            json.dump(self.metrics.to_dict(), f, indent=2)
        
        return filepath
    
    def print_summary(self) -> None:
        """Print a formatted summary of performance metrics."""
        metrics_dict = self.metrics.to_dict()
        
        print("\n" + "="*50)
        print("PERFORMANCE METRICS SUMMARY")
        print("="*50)
        print(f"Task ID: {metrics_dict['task_id']}")
        print(f"Task Goal: {metrics_dict['task_goal']}")
        print(f"Status: {'✓ SUCCESS' if metrics_dict['success'] else '✗ FAILED'}")
        
        if metrics_dict['error_message']:
            print(f"Error: {metrics_dict['error_message']}")
        
        print(f"\nTotal Steps: {metrics_dict['total_steps']}")
        print(f"Total Time: {metrics_dict['total_time']:.2f}s")
        print(f"Average Step Time: {metrics_dict['average_step_time']:.3f}s")
        print(f"Step Efficiency: {metrics_dict['step_efficiency']:.2f} steps/sec")
        print("="*50 + "\n")
