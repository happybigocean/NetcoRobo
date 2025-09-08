import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from mcp.server.fastmcp import FastMCP
import sqlite3
import aiosqlite
import os

# Initialize MCP server
calendar_mcp = FastMCP("CEO Agent Calendar Server")

# Calendar database path
CALENDAR_DB_PATH = "./database/calendar.db"

async def init_calendar_db():
    """Initialize calendar database"""
    os.makedirs(os.path.dirname(CALENDAR_DB_PATH), exist_ok=True)
    
    async with aiosqlite.connect(CALENDAR_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                start_datetime TEXT NOT NULL,
                end_datetime TEXT NOT NULL,
                event_type TEXT DEFAULT 'meeting',
                priority TEXT DEFAULT 'medium',
                attendees JSON,
                location TEXT,
                reminder_minutes INTEGER DEFAULT 15,
                status TEXT DEFAULT 'scheduled',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX(agent_id),
                INDEX(start_datetime),
                INDEX(event_type)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS calendar_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                agent_id TEXT NOT NULL,
                reminder_datetime TEXT NOT NULL,
                message TEXT NOT NULL,
                sent BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES calendar_events (id),
                INDEX(agent_id),
                INDEX(reminder_datetime),
                INDEX(sent)
            )
        """)
        
        await db.commit()

@calendar_mcp.tool()
async def create_event(
    agent_id: str,
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    event_type: str = "meeting",
    priority: str = "medium",
    attendees: str = "[]",
    location: str = "",
    reminder_minutes: int = 15
) -> str:
    """
    Create a calendar event
    
    Args:
        agent_id: ID of the agent creating the event
        title: Event title
        start_datetime: Start date/time in ISO format
        end_datetime: End date/time in ISO format
        description: Event description
        event_type: Type of event (meeting, deadline, reminder, task)
        priority: Priority (low, medium, high, urgent)
        attendees: JSON array of attendees
        location: Event location
        reminder_minutes: Minutes before event to remind
    """
    try:
        attendees_list = json.loads(attendees) if attendees else []
        
        async with aiosqlite.connect(CALENDAR_DB_PATH) as db:
            cursor = await db.execute(
                """INSERT INTO calendar_events 
                   (agent_id, title, description, start_datetime, end_datetime, 
                    event_type, priority, attendees, location, reminder_minutes) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (agent_id, title, description, start_datetime, end_datetime,
                 event_type, priority, json.dumps(attendees_list), location, reminder_minutes)
            )
            
            event_id = cursor.lastrowid
            await db.commit()
            
            # Create reminder if requested
            if reminder_minutes > 0:
                reminder_datetime = (datetime.fromisoformat(start_datetime.replace('Z', '+00:00')) - 
                                   timedelta(minutes=reminder_minutes)).isoformat()
                
                await db.execute(
                    """INSERT INTO calendar_reminders 
                       (event_id, agent_id, reminder_datetime, message) 
                       VALUES (?, ?, ?, ?)""",
                    (event_id, agent_id, reminder_datetime, f"Reminder: {title} in {reminder_minutes} minutes")
                )
                await db.commit()
        
        return json.dumps({
            "success": True,
            "event_id": event_id,
            "message": f"Event '{title}' created successfully",
            "start_datetime": start_datetime,
            "reminder_set": reminder_minutes > 0
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to create event: {str(e)}"
        })

@calendar_mcp.tool()
async def get_events(
    agent_id: str,
    start_date: str = "",
    end_date: str = "",
    event_type: str = "",
    limit: int = 50
) -> str:
    """
    Get calendar events for an agent
    
    Args:
        agent_id: ID of the agent
        start_date: Start date filter (ISO format)
        end_date: End date filter (ISO format)
        event_type: Filter by event type
        limit: Maximum number of events to return
    """
    try:
        async with aiosqlite.connect(CALENDAR_DB_PATH) as db:
            query = "SELECT * FROM calendar_events WHERE agent_id = ?"
            params = [agent_id]
            
            if start_date:
                query += " AND start_datetime >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND start_datetime <= ?"
                params.append(end_date)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            query += " ORDER BY start_datetime ASC LIMIT ?"
            params.append(limit)
            
            async with db.execute(query, params) as cursor:
                events = []
                async for row in cursor:
                    events.append({
                        "id": row[0],
                        "agent_id": row[1],
                        "title": row[2],
                        "description": row[3],
                        "start_datetime": row[4],
                        "end_datetime": row[5],
                        "event_type": row[6],
                        "priority": row[7],
                        "attendees": json.loads(row[8]) if row[8] else [],
                        "location": row[9],
                        "reminder_minutes": row[10],
                        "status": row[11],
                        "created_at": row[12],
                        "updated_at": row[13]
                    })
        
        return json.dumps({
            "success": True,
            "events": events,
            "count": len(events)
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get events: {str(e)}"
        })

@calendar_mcp.tool()
async def update_event_status(
    event_id: int,
    status: str,
    notes: str = ""
) -> str:
    """
    Update event status
    
    Args:
        event_id: ID of the event
        status: New status (scheduled, in_progress, completed, cancelled)
        notes: Additional notes
    """
    try:
        async with aiosqlite.connect(CALENDAR_DB_PATH) as db:
            await db.execute(
                """UPDATE calendar_events 
                   SET status = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (status, event_id)
            )
            await db.commit()
        
        return json.dumps({
            "success": True,
            "event_id": event_id,
            "new_status": status,
            "message": f"Event {event_id} status updated to {status}"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to update event status: {str(e)}"
        })

@calendar_mcp.tool()
async def get_upcoming_reminders(
    agent_id: str,
    hours_ahead: int = 24
) -> str:
    """
    Get upcoming reminders for an agent
    
    Args:
        agent_id: ID of the agent
        hours_ahead: How many hours ahead to look for reminders
    """
    try:
        cutoff_time = (datetime.now() + timedelta(hours=hours_ahead)).isoformat()
        current_time = datetime.now().isoformat()
        
        async with aiosqlite.connect(CALENDAR_DB_PATH) as db:
            async with db.execute(
                """SELECT r.*, e.title, e.start_datetime 
                   FROM calendar_reminders r
                   JOIN calendar_events e ON r.event_id = e.id
                   WHERE r.agent_id = ? 
                   AND r.reminder_datetime BETWEEN ? AND ?
                   AND r.sent = FALSE
                   ORDER BY r.reminder_datetime ASC""",
                (agent_id, current_time, cutoff_time)
            ) as cursor:
                reminders = []
                async for row in cursor:
                    reminders.append({
                        "reminder_id": row[0],
                        "event_id": row[1],
                        "reminder_datetime": row[3],
                        "message": row[4],
                        "event_title": row[6],
                        "event_start": row[7]
                    })
        
        return json.dumps({
            "success": True,
            "reminders": reminders,
            "count": len(reminders)
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get reminders: {str(e)}"
        })

# Initialize database on startup
async def startup():
    await init_calendar_db()
    print("✅ Calendar MCP Server initialized")

if __name__ == "__main__":
    print("📅 Starting Calendar MCP Server...")
    asyncio.run(startup())
    asyncio.run(calendar_mcp.run())