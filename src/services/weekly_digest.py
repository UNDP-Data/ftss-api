"""
Service for generating and sending weekly digests of signals.
"""

import logging
import datetime
from typing import List, Dict, Any, Optional
from datetime import timedelta

from ..entities import Signal, SignalFilters, Status
from ..database import signals, connection

logger = logging.getLogger(__name__)

class WeeklyDigestService:
    """Service class for generating and sending weekly digests of signals."""
    
    def __init__(self):
        """Initialize the weekly digest service."""
        pass

    async def get_recent_signals(self, days: Optional[int] = None, status: Optional[List[Status]] = None, limit: Optional[int] = None) -> List[Signal]:
        """
        Get signals filtered by optional days, status, and limit.
        If no filters are provided, fetch the last 10 draft signals.
        """
        logger.info(f"Getting signals with filters - days: {days}, status: {status}, limit: {limit}")
        start_time = datetime.datetime.now()
        # Set defaults if not provided
        if status is None:
            status = [Status.DRAFT]
        if limit is None:
            limit = 10
        # Calculate date range if days is provided
        end_date = datetime.datetime.now()
        start_date = end_date - timedelta(days=days) if days is not None else None
        start_date_str = start_date.strftime("%Y-%m-%d") if start_date else None
        logger.info(f"Date range: {start_date_str} to {end_date.strftime('%Y-%m-%d') if start_date else 'ALL'}")
        filters = SignalFilters(
            statuses=status,
            per_page=limit
        )
        logger.debug("Opening database connection for signal fetch...")
        async with await connection.get_connection() as conn:
            logger.debug("Database connection established.")
            async with conn.cursor() as cursor:
                logger.debug("Cursor opened. Preparing to execute signal fetch query...")
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
                        {f'AND created_at >= %(start_date)s' if start_date_str else ''}
                    ORDER BY
                        created_at DESC
                    LIMIT
                        %(limit)s
                    ;
                """
                filter_params = filters.model_dump()
                filter_params['limit'] = limit
                if start_date_str:
                    filter_params['start_date'] = start_date_str
                logger.debug(f"Executing query with params: {filter_params}")
                await cursor.execute(query, filter_params)
                logger.debug("Query executed. Fetching rows...")
                rows = await cursor.fetchall()
                logger.debug(f"Fetched {len(rows)} rows from database.")
                signals_list = [Signal(**dict(row)) for row in rows]
                logger.info(f"Found {len(signals_list)} signals with filters - days: {days}, status: {status}, limit: {limit}")
                elapsed = (datetime.datetime.now() - start_time).total_seconds()
                logger.info(f"Signal fetch took {elapsed:.2f} seconds.")
                return signals_list

    def generate_email_html(self, signals_list: List[Signal], intro_text: Optional[str] = None) -> str:
        """
        Generate HTML content for the weekly digest email.
        
        Parameters
        ----------
        signals_list : List[Signal]
            List of signals to include in the digest.
        intro_text : Optional[str]
            Optional custom introduction text.
            
        Returns
        -------
        str
            HTML content for the email.
        """
        if not signals_list:
            logger.warning("No signals to include in digest")
            return "<p>No new signals were found for this period.</p>"
        
        default_intro = """
        <p>Hello,</p>
        <p>Here's your weekly digest of new signals from the UNDP Futures platform. 
        Below are the latest signals that might be of interest:</p>
        """
        
        intro = intro_text or default_intro
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>UNDP Futures - Weekly Signal Digest</title>
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
            </style>
        </head>
        <body>
            <div class="header">
                <h1>UNDP Futures - Weekly Signal Digest</h1>
                <p>Stay updated with the latest signals from around the world</p>
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
            
            html += f"""
            <div class="signal">
                <h3>{signal.headline}</h3>
                <div class="signal-meta">
                    <strong>Location:</strong> {location_text} 
                    {f'• <strong>Source:</strong> <a href="{signal.url}" target="_blank">View Source</a>' if signal.url else ''}
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
                <p>This email was sent by the UNDP Futures platform. To manage your notification preferences, please contact your administrator.</p>
                <p>&copy; United Nations Development Programme</p>
            </div>
        </body>
        </html>
        """
        
        return html

    async def generate_and_send_digest(self, 
                                      recipients: List[str], 
                                      days: int = 7, 
                                      subject: Optional[str] = None,
                                      custom_intro: Optional[str] = None,
                                      status: Optional[List[Status]] = None,
                                      limit: Optional[int] = None) -> bool:
        """
        Generate and send a weekly digest email to specified recipients.
        
        Parameters
        ----------
        recipients : List[str]
            List of email addresses to send the digest to.
        days : int, optional
            Number of days to look back for signals, defaults to 7.
        subject : Optional[str], optional
            Custom email subject, defaults to standard subject with date.
        custom_intro : Optional[str], optional
            Custom introduction text for the email.
        status : Optional[List[Status]], optional
            List of signal statuses to filter by.
        limit : Optional[int], optional
            Maximum number of signals to include.
        
        Returns
        -------
        bool
            True if the email was sent successfully, False otherwise.
        """
        if not recipients:
            logger.error("No recipients specified for weekly digest")
            return False
        logger.info(f"Generating weekly digest email for {len(recipients)} recipients")
        step_start = datetime.datetime.now()
        logger.info("Fetching recent signals for digest...")
        signals_list = await self.get_recent_signals(days=days, status=status, limit=limit)
        logger.info(f"Fetched {len(signals_list)} signals for digest.")
        logger.info(f"Signal fetch step took {(datetime.datetime.now() - step_start).total_seconds():.2f} seconds.")
        if not signals_list:
            logger.warning("No signals found for digest, skipping email send")
            return False
        logger.info("Generating HTML content for digest email...")
        html_start = datetime.datetime.now()
        html_content = self.generate_email_html(signals_list, custom_intro)
        logger.info(f"HTML generation took {(datetime.datetime.now() - html_start).total_seconds():.2f} seconds.")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        email_subject = subject or f"UNDP Futures Weekly Digest - {today}"
        from .email_factory import create_email_service
        logger.info("Creating email service...")
        email_service = create_email_service()
        logger.info(f"Sending weekly digest email to {recipients} with subject {email_subject}")
        send_start = datetime.datetime.now()
        try:
            success = await email_service.send_email(
                to_emails=recipients,
                subject=email_subject,
                content=html_content,
                content_type="text/html"
            )
            logger.info(f"Email send step took {(datetime.datetime.now() - send_start).total_seconds():.2f} seconds.")
            if success:
                logger.info(f"Weekly digest email sent successfully to {len(recipients)} recipients")
            else:
                logger.error("Failed to send weekly digest email")
            return success
        except Exception as e:
            logger.error(f"Error sending weekly digest email: {e}", exc_info=True)
            return False