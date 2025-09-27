"""
Database module for the Mental Health Bot

This module provides SQLite database management with
automatic migration support from legacy JSON format.
"""

from .migration import DatabaseMigration

__all__ = ['DatabaseMigration']
