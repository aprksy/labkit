"""
timer.py: Infrastructure for timer-based plugin triggers
"""
import abc
import threading
import time
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import logging



class TimerTrigger(abc.ABC):
    """
    TimerTrigger: Base class for plugins that need timer-based execution
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"plugin.timer.{name}")
        self.timer_thread: Optional[threading.Timer] = None
        self.active_timers: Dict[str, threading.Timer] = {}
        self.timer_callbacks: Dict[str, Callable] = {}

    def schedule_once(self, callback: Callable, delay: float, timer_id: str = None) -> str:
        """
        Schedule a one-time execution of a callback
        :param callback: Function to call when timer expires
        :param delay: Delay in seconds before execution
        :param timer_id: Optional ID for the timer (auto-generated if not provided)
        :return: Timer ID
        """
        if timer_id is None:
            timer_id = f"{self.name}_once_{int(time.time() * 1000000)}"
        
        # Cancel if already scheduled
        if timer_id in self.active_timers:
            self.cancel_timer(timer_id)
        
        timer = threading.Timer(delay, callback)
        timer.daemon = True
        timer.start()
        self.active_timers[timer_id] = timer
        self.timer_callbacks[timer_id] = callback
        
        self.logger.info(f"Scheduled one-time timer {timer_id} for {delay}s in {self.name}")
        return timer_id

    def schedule_recurring(self, callback: Callable, interval: float, timer_id: str = None) -> str:
        """
        Schedule a recurring execution of a callback
        :param callback: Function to call when timer expires
        :param interval: Interval in seconds between executions
        :param timer_id: Optional ID for the timer (auto-generated if not provided)
        :return: Timer ID
        """
        if timer_id is None:
            timer_id = f"{self.name}_recur_{int(time.time() * 1000000)}"
        
        def recurring_wrapper():
            try:
                callback()
            finally:
                # Reschedule the timer for the next execution
                if timer_id in self.active_timers:
                    next_timer = threading.Timer(interval, recurring_wrapper)
                    next_timer.daemon = True
                    next_timer.start()
                    self.active_timers[timer_id] = next_timer
        
        # Cancel if already scheduled
        if timer_id in self.active_timers:
            self.cancel_timer(timer_id)
        
        timer = threading.Timer(interval, recurring_wrapper)
        timer.daemon = True
        timer.start()
        self.active_timers[timer_id] = timer
        self.timer_callbacks[timer_id] = callback
        
        self.logger.info(f"Scheduled recurring timer {timer_id} for {interval}s interval in {self.name}")
        return timer_id

    def cancel_timer(self, timer_id: str) -> bool:
        """
        Cancel a scheduled timer
        :param timer_id: ID of the timer to cancel
        :return: True if cancellation succeeds
        """
        if timer_id in self.active_timers:
            timer = self.active_timers[timer_id]
            timer.cancel()
            del self.active_timers[timer_id]
            if timer_id in self.timer_callbacks:
                del self.timer_callbacks[timer_id]
            self.logger.info(f"Cancelled timer {timer_id} in {self.name}")
            return True
        return False

    def get_active_timers(self) -> Dict[str, float]:
        """
        Get list of active timers and their remaining time
        :return: Dictionary of timer IDs and remaining time in seconds
        """
        active = {}
        for timer_id, timer in self.active_timers.items():
            # Unfortunately, threading.Timer doesn't expose remaining time directly
            # We'll just return the timer IDs for now
            active[timer_id] = -1  # Unknown remaining time
        return active

    def cleanup(self):
        """
        Clean up all active timers
        """
        for timer_id in list(self.active_timers.keys()):
            self.cancel_timer(timer_id)
        self.active_timers.clear()
        self.timer_callbacks.clear()


class ConditionalTimerTrigger(TimerTrigger):
    """
    ConditionalTimerTrigger: Timer trigger that can execute based on conditions
    Useful for scenarios like waiting for IP assignment
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.condition_timers: Dict[str, tuple] = {}  # timer_id -> (condition_func, action_func, max_attempts)

    def schedule_with_condition(self, 
                               condition_func: Callable[[], bool], 
                               action_func: Callable, 
                               check_interval: float = 1.0,
                               max_attempts: int = 30,
                               timer_id: str = None) -> str:
        """
        Schedule an action to execute when a condition is met
        :param condition_func: Function that returns True when condition is met
        :param action_func: Function to execute when condition is met
        :param check_interval: Interval in seconds between condition checks
        :param max_attempts: Maximum number of attempts before giving up
        :param timer_id: Optional ID for the timer
        :return: Timer ID
        """
        if timer_id is None:
            timer_id = f"{self.name}_cond_{int(time.time() * 1000000)}"
        
        attempt_count = 0
        
        def condition_checker():
            nonlocal attempt_count
            attempt_count += 1
            
            if condition_func():
                # Condition met, execute action
                try:
                    action_func()
                    self.logger.info(f"Condition met for {timer_id}, executed action")
                finally:
                    # Remove the timer after execution
                    if timer_id in self.condition_timers:
                        del self.condition_timers[timer_id]
                    self.cancel_timer(timer_id)
            elif attempt_count >= max_attempts:
                # Max attempts reached, give up
                self.logger.warning(f"Max attempts reached for conditional timer {timer_id}")
                if timer_id in self.condition_timers:
                    del self.condition_timers[timer_id]
                self.cancel_timer(timer_id)
            else:
                # Condition not met yet, reschedule check
                next_timer = threading.Timer(check_interval, condition_checker)
                next_timer.daemon = True
                next_timer.start()
                self.active_timers[timer_id] = next_timer
        
        # Cancel if already scheduled
        if timer_id in self.active_timers:
            self.cancel_timer(timer_id)
        
        # Store condition info
        self.condition_timers[timer_id] = (condition_func, action_func, max_attempts)
        
        # Start the first check
        timer = threading.Timer(check_interval, condition_checker)
        timer.daemon = True
        timer.start()
        self.active_timers[timer_id] = timer
        
        self.logger.info(f"Scheduled conditional timer {timer_id} with {max_attempts} attempts in {self.name}")
        return timer_id

    def cleanup(self):
        """
        Clean up all active timers including conditional ones
        """
        # Clean up regular timers
        super().cleanup()
        # Clean up conditional timers
        self.condition_timers.clear()