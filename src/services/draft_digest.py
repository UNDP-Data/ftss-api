"""
Service for generating digests of draft signals.
This is a specialized version of the weekly digest service that focuses on draft signals.
"""

import logging
import datetime
from typing import List, Dict, Any, Optional
from datetime import timedelta

from ..entities import Signal, SignalFilters, Status
from ..database import signals, connection

logger = logging.getLogger(__name__)

class DraftDigestService:
    """Service class for generating digests of draft signals."""
    
    def __init__(self):
        """Initialize the draft digest service."""
        pass

    async def get_recent_draft_signals(self, days: int = 7) -> List[Signal]:
        """
        Get draft signals created in the last specified number of days.
        
        Parameters
        ----------
        days : int, optional
            The number of days to look back, defaults to 7 days.
            
        Returns
        -------
        List[Signal]
            A list of draft signals created in the specified period.
        """
        logger.info(f"Getting draft signals from the last {days} days")
        
        # Calculate date range
        end_date = datetime.datetime.now()
        start_date = end_date - timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%d")
        
        logger.info(f"Date range: {start_date_str} to {end_date.strftime('%Y-%m-%d')}")
        
        # Create signal filters - specifically for DRAFT status
        filters = SignalFilters(
            statuses=[Status.DRAFT],  # Only draft signals
            # We'll filter by created_at in SQL directly
            limit=100  # Limit the number of signals
        )
        
        # Use a DB connection to fetch signals
        async with await connection.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Get signals created after start_date
                query = f"""
                    SELECT 
                        *, COUNT(*) OVER() AS total_count
                    FROM
                        signals AS s
                    LEFT OUTER JOIN (
                        SELECT
                            signal_id, array_agg(trend_id) AS connected_trends
                        FROM
                            connections
                        GROUP BY
                            signal_id
                        ) AS c
                    ON
                        s.id = c.signal_id
                    LEFT OUTER JOIN (
                        SELECT
                            name AS unit_name,
                            region AS unit_region
                        FROM
                            units
                        ) AS u
                    ON
                        s.created_unit = u.unit_name
                    LEFT OUTER JOIN (
                        SELECT
                            name AS location,
                            region AS location_region,
                            bureau AS location_bureau
                        FROM
                            locations
                        ) AS l
                    ON
                        s.location = l.location
                    WHERE
                        status = ANY(%(statuses)s)
                        AND created_at >= %(start_date)s
                    ORDER BY
                        created_at DESC
                    LIMIT
                        %(limit)s
                    ;
                """
                
                # Add start_date parameter to the filters
                filter_params = filters.model_dump()
                filter_params['start_date'] = start_date_str
                
                await cursor.execute(query, filter_params)
                rows = await cursor.fetchall()
                
                signals_list = [Signal(**row) for row in rows]
                
                logger.info(f"Found {len(signals_list)} draft signals from the last {days} days")
                return signals_list
    
    async def get_signals_by_status(self, statuses: List[Status], days: int = 7) -> List[Signal]:
        """
        Get signals with specified statuses created in the last specified number of days.
        
        Parameters
        ----------
        statuses : List[Status]
            List of statuses to filter by (e.g., [Status.DRAFT, Status.PENDING])
        days : int, optional
            The number of days to look back, defaults to 7 days.
            
        Returns
        -------
        List[Signal]
            A list of signals with the specified statuses created in the specified period.
        """
        logger.info(f"Getting signals with statuses {statuses} from the last {days} days")
        
        # Calculate date range
        end_date = datetime.datetime.now()
        start_date = end_date - timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%d")
        
        logger.info(f"Date range: {start_date_str} to {end_date.strftime('%Y-%m-%d')}")
        
        # Create signal filters with the specified statuses
        filters = SignalFilters(
            statuses=statuses,
            # We'll filter by created_at in SQL directly
            limit=100  # Limit the number of signals
        )
        
        # Use a DB connection to fetch signals
        async with await connection.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Get signals created after start_date
                query = f"""
                    SELECT 
                        *, COUNT(*) OVER() AS total_count
                    FROM
                        signals AS s
                    LEFT OUTER JOIN (
                        SELECT
                            signal_id, array_agg(trend_id) AS connected_trends
                        FROM
                            connections
                        GROUP BY
                            signal_id
                        ) AS c
                    ON
                        s.id = c.signal_id
                    LEFT OUTER JOIN (
                        SELECT
                            name AS unit_name,
                            region AS unit_region
                        FROM
                            units
                        ) AS u
                    ON
                        s.created_unit = u.unit_name
                    LEFT OUTER JOIN (
                        SELECT
                            name AS location,
                            region AS location_region,
                            bureau AS location_bureau
                        FROM
                            locations
                        ) AS l
                    ON
                        s.location = l.location
                    WHERE
                        status = ANY(%(statuses)s)
                        AND created_at >= %(start_date)s
                    ORDER BY
                        created_at DESC
                    LIMIT
                        %(limit)s
                    ;
                """
                
                # Add start_date parameter to the filters
                filter_params = filters.model_dump()
                filter_params['start_date'] = start_date_str
                
                await cursor.execute(query, filter_params)
                rows = await cursor.fetchall()
                
                signals_list = [Signal(**row) for row in rows]
                
                status_names = [s.value for s in statuses]
                logger.info(f"Found {len(signals_list)} signals with statuses {status_names} from the last {days} days")
                return signals_list

    def generate_digest_html(self, signals_list: List[Signal], intro_text: Optional[str] = None, title: str = "Signal Digest") -> str:
        """
        Generate HTML content for the digest.
        
        Parameters
        ----------
        signals_list : List[Signal]
            List of signals to include in the digest.
        intro_text : Optional[str]
            Optional custom introduction text.
        title : str
            Title for the digest page.
            
        Returns
        -------
        str
            HTML content for the digest.
        """
        if not signals_list:
            logger.warning("No signals to include in digest")
            return "<p>No signals were found for this period.</p>"
        
        default_intro = """
        <p>Here's a digest of signals from the UNDP Futures platform. 
        Below are the latest signals:</p>
        """
        
        intro = intro_text or default_intro
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>UNDP Futures - {title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #0768AC;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .signal {{
                    margin-bottom: 30px;
                    padding: 15px;
                    border-left: 4px solid #0768AC;
                    background-color: #f5f5f5;
                }}
                .signal h3 {{
                    margin-top: 0;
                    color: #0768AC;
                }}
                .signal-meta {{
                    font-size: 0.9em;
                    color: #666;
                    margin-bottom: 10px;
                }}
                .keywords {{
                    display: inline-block;
                    background-color: #e0f0ff;
                    padding: 2px 8px;
                    margin-right: 5px;
                    border-radius: 10px;
                    font-size: 0.85em;
                }}
                .status {{
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 10px;
                    font-size: 0.85em;
                    font-weight: bold;
                    margin-left: 10px;
                }}
                .status-draft {{
                    background-color: #ffe6cc;
                    color: #995200;
                }}
                .status-pending {{
                    background-color: #e6f2ff;
                    color: #004d99;
                }}
                .status-approved {{
                    background-color: #e6ffe6;
                    color: #006600;
                }}
                .status-rejected {{
                    background-color: #ffe6e6;
                    color: #cc0000;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 15px;
                    border-top: 1px solid #ddd;
                    font-size: 0.9em;
                    color: #666;
                    text-align: center;
                }}
                a {{
                    color: #0768AC;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                .timestamp {{
                    color: #666;
                    font-size: 0.8em;
                    font-style: italic;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>UNDP Futures - {title}</h1>
                <p>Signals from the UNDP Futures platform</p>
                <p class="timestamp">Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
            </div>
            
            {intro}
            
            <div class="signals-container">
        """
        
        # Add each signal to the HTML
        for signal in signals_list:
            keywords_html = ""
            if signal.keywords:
                keywords_html = " ".join([f'<span class="keywords">{k}</span>' for k in signal.keywords])
            
            location_text = signal.location or "Global"
            
            # Add status class
            status_class = f"status-{signal.status.lower()}" if hasattr(signal, 'status') else ""
            status_text = signal.status.capitalize() if hasattr(signal, 'status') else "Unknown"
            
            # Format created date
            created_date = ""
            if hasattr(signal, 'created_at') and signal.created_at:
                if isinstance(signal.created_at, str):
                    created_date = signal.created_at
                else:
                    try:
                        created_date = signal.created_at.strftime("%Y-%m-%d")
                    except:
                        created_date = str(signal.created_at)
            
            html += f"""
            <div class="signal">
                <h3>{signal.headline} <span class="status {status_class}">{status_text}</span></h3>
                <div class="signal-meta">
                    <strong>Location:</strong> {location_text}
                    {f'• <strong>Source:</strong> <a href="{signal.url}" target="_blank">View Source</a>' if hasattr(signal, 'url') and signal.url else ''}
                    {f'• <strong>Created:</strong> {created_date}' if created_date else ''}
                    {f'• <strong>Created by:</strong> {signal.created_by}' if hasattr(signal, 'created_by') and signal.created_by else ''}
                </div>
                <p>{signal.description}</p>
                <div>
                    {keywords_html}
                </div>
            </div>
            """
        
        html += """
            </div>
            
            <div class="footer">
                <p>UNDP Futures platform signal digest</p>
                <p>&copy; United Nations Development Programme</p>
            </div>
        </body>
        </html>
        """
        
        return html