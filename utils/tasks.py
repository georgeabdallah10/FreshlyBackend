"""
Background tasks for handling long-running operations
"""
import logging
import asyncio
from typing import Any, Callable, Dict, Optional
from datetime import datetime
import traceback

from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)


class TaskManager:
    """Manage background tasks with status tracking"""
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

    def add_task(
        self, 
        task_id: str, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> str:
        """Add a background task"""
        self._tasks[task_id] = {
            'status': 'pending',
            'created_at': datetime.now(),
            'started_at': None,
            'completed_at': None,
            'result': None,
            'error': None
        }
        
        # Create and start the task
        task = asyncio.create_task(self._run_task(task_id, func, *args, **kwargs))
        self._running_tasks[task_id] = task
        
        logger.info(f"Background task created: {task_id}")
        return task_id

    async def _run_task(self, task_id: str, func: Callable, *args, **kwargs):
        """Run the task and update status"""
        try:
            self._tasks[task_id]['status'] = 'running'
            self._tasks[task_id]['started_at'] = datetime.now()
            
            logger.info(f"Starting background task: {task_id}")
            
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._tasks[task_id]['status'] = 'completed'
            self._tasks[task_id]['completed_at'] = datetime.now()
            self._tasks[task_id]['result'] = result
            
            logger.info(f"Background task completed: {task_id}")
            
        except Exception as e:
            self._tasks[task_id]['status'] = 'failed'
            self._tasks[task_id]['completed_at'] = datetime.now()
            self._tasks[task_id]['error'] = str(e)
            
            logger.error(f"Background task failed: {task_id} - {e}")
            logger.error(traceback.format_exc())
        
        finally:
            # Remove from running tasks
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        return self._tasks.get(task_id)

    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        """List all tasks"""
        return self._tasks.copy()

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            task.cancel()
            self._tasks[task_id]['status'] = 'cancelled'
            self._tasks[task_id]['completed_at'] = datetime.now()
            del self._running_tasks[task_id]
            logger.info(f"Background task cancelled: {task_id}")
            return True
        return False

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        
        tasks_to_remove = []
        for task_id, task_info in self._tasks.items():
            if (task_info['completed_at'] and 
                task_info['completed_at'].timestamp() < cutoff):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self._tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old background tasks")


# Global task manager
task_manager = TaskManager()


# Common background tasks
async def send_email_task(to_email: str, subject: str, body: str):
    """Background task for sending emails"""
    try:
        from core.email_utils import send_email
        await send_email(to_email, subject, body)
        logger.info(f"Email sent successfully to {to_email}")
        return {"status": "sent", "to": to_email}
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        raise


async def process_file_upload_task(file_path: str, user_id: int):
    """Background task for processing file uploads"""
    try:
        # Simulate file processing (resize images, etc.)
        await asyncio.sleep(2)  # Simulate processing time
        
        logger.info(f"File processed successfully: {file_path} for user {user_id}")
        return {"status": "processed", "file_path": file_path, "user_id": user_id}
    except Exception as e:
        logger.error(f"Failed to process file {file_path}: {e}")
        raise


async def generate_meal_plan_task(user_id: int, preferences: Dict[str, Any]):
    """Background task for generating meal plans using AI"""
    try:
        # Simulate AI meal plan generation
        await asyncio.sleep(5)  # Simulate AI processing time
        
        # Mock meal plan
        meal_plan = {
            "user_id": user_id,
            "meals": [
                {"day": "Monday", "breakfast": "Oatmeal", "lunch": "Salad", "dinner": "Chicken"},
                {"day": "Tuesday", "breakfast": "Eggs", "lunch": "Soup", "dinner": "Fish"},
                # ... more meals
            ],
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Meal plan generated for user {user_id}")
        return meal_plan
    except Exception as e:
        logger.error(f"Failed to generate meal plan for user {user_id}: {e}")
        raise


async def cache_popular_recipes_task():
    """Background task to cache popular recipes"""
    try:
        # This would typically query the database for popular recipes
        # and cache them for faster access
        await asyncio.sleep(3)  # Simulate database query time
        
        logger.info("Popular recipes cached successfully")
        return {"status": "cached", "count": 50}
    except Exception as e:
        logger.error(f"Failed to cache popular recipes: {e}")
        raise


# Background task cleanup scheduler
async def task_cleanup_scheduler():
    """Periodic cleanup of old background tasks"""
    while True:
        try:
            task_manager.cleanup_old_tasks()
            await asyncio.sleep(3600)  # Run every hour
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Task cleanup scheduler error: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retry
