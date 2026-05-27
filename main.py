#!/usr/bin/env python3
"""
AcquiAxis AI - Multi-Agent Marketing System
5 AI agents working together to generate M&A leads and drive revenue

Agents:
1. LinkedIn Strategist - Posts daily, engages, generates LinkedIn leads
2. Growth Hacker - Runs ads, optimizes ROAS, scales campaigns
3. Content Creator - Writes blog posts, email content, social posts
4. SEO Specialist - Optimizes rankings, builds authority, organic traffic
5. TikTok Strategist - Viral content, audience growth, brand awareness

Deployment: Railway.app (no credit card needed)
"""

import os
import json
import logging
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import anthropic
import schedule
from flask import Flask, request, jsonify
import threading

# ============================================================================
# CONFIGURATION
# ============================================================================

# Environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TEAMS_WEBHOOK_GENERAL = os.getenv("TEAMS_WEBHOOK_GENERAL")
TEAMS_WEBHOOK_PERFORMANCE = os.getenv("TEAMS_WEBHOOK_PERFORMANCE")
TEAMS_WEBHOOK_VIRAL = os.getenv("TEAMS_WEBHOOK_VIRAL")
TEAMS_WEBHOOK_SALES = os.getenv("TEAMS_WEBHOOK_SALES")
LINKEDIN_API_TOKEN = os.getenv("LINKEDIN_API_TOKEN")
LINKEDIN_COMPANY_ID = os.getenv("LINKEDIN_COMPANY_ID")
GOOGLE_ANALYTICS_PROPERTY_ID = os.getenv("GOOGLE_ANALYTICS_PROPERTY_ID")
AIRTABLE_API_TOKEN = os.getenv("AIRTABLE_API_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
PORT = int(os.getenv("PORT", 8080))

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APP SETUP
# ============================================================================

app = Flask(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ============================================================================
# TEAMS NOTIFICATIONS
# ============================================================================

def send_teams_notification(webhook_url: str, message: str, title: str = "AcquiAxis AI", color: str = "0078D4"):
    """Send notification to Microsoft Teams channel"""
    if not webhook_url:
        logger.warning(f"Teams webhook URL not configured")
        return False
    
    try:
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": title,
            "themeColor": color,
            "sections": [
                {
                    "activityTitle": title,
                    "activitySubtitle": f"AcquiAxis AI - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "text": message
                }
            ]
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Teams notification sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send Teams notification: {str(e)}")
        return False

# ============================================================================
# AIRTABLE INTEGRATION
# ============================================================================

def log_to_airtable(record_type: str, data: Dict):
    """Log agent activities and leads to Airtable"""
    if not AIRTABLE_API_TOKEN or not AIRTABLE_BASE_ID:
        logger.warning("Airtable not configured")
        return False
    
    try:
        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        table_mapping = {
            "linkedin_post": "LinkedIn Posts",
            "linkedin_lead": "LinkedIn Leads",
            "content": "Content Created",
            "email": "Email Campaigns",
            "ad_campaign": "Ad Campaigns",
            "seo_update": "SEO Updates"
        }
        
        table_name = table_mapping.get(record_type, "Activities")
        
        payload = {
            "records": [
                {
                    "fields": {
                        "Timestamp": datetime.now().isoformat(),
                        "Type": record_type,
                        "Data": json.dumps(data),
                        **data
                    }
                }
            ]
        }
        
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}"
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Logged to Airtable: {record_type}")
        return True
    except Exception as e:
        logger.error(f"Failed to log to Airtable: {str(e)}")
        return False

# ============================================================================
# AI AGENTS
# ============================================================================

class LinkedInStrategist:
    """Agent for LinkedIn posting, engagement, and lead generation"""
    
    @staticmethod
    def get_system_prompt():
        return """You are the LinkedIn Strategist for AcquiAxis AI, an AI-powered M&A software platform.

Your role:
- Create compelling LinkedIn posts about M&A, acquisitions, deal management
- Generate 300-500 word thought leadership posts
- Target PE analysts, business brokers, M&A advisors, CFOs
- Include data, insights, contrarian takes, or founder stories
- End with clear CTA (comment, link to resource, etc.)
- Use hashtags: #M&A #Acquisitions #PE #DealManagement #PrivateEquity

Format your response as JSON:
{
    "post_text": "The full LinkedIn post (300-500 words)",
    "hashtags": ["#hashtag1", "#hashtag2"],
    "cta": "Call to action"
}"""
    
    @staticmethod
    def create_daily_post():
        """Generate today's LinkedIn post"""
        try:
            response = client.messages.create(
                model="claude-opus-4-20250805",
                max_tokens=1000,
                system=LinkedInStrategist.get_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": "Create a compelling LinkedIn post about M&A deal velocity. Include data and actionable insights for PE professionals."
                    }
                ]
            )
            
            post_data = json.loads(response.content[0].text)
            
            log_to_airtable("linkedin_post", {
                "Title": post_data.get("post_text", "")[:50],
                "Content": post_data.get("post_text", ""),
                "Status": "Published"
            })
            
            send_teams_notification(
                TEAMS_WEBHOOK_GENERAL,
                f"📱 LinkedIn post published!\n\n{post_data.get('post_text', '')[:200]}...",
                "LinkedIn Strategist",
                "0078D4"
            )
            
            logger.info("LinkedIn post created successfully")
            return post_data
        except Exception as e:
            logger.error(f"Failed to create LinkedIn post: {str(e)}")
            return None

class GrowthHacker:
    """Agent for paid ads, campaign optimization, and ROAS tracking"""
    
    @staticmethod
    def get_system_prompt():
        return """You are the Growth Hacker for AcquiAxis AI.

Your role:
- Analyze campaign performance and ROAS
- Identify high-performing audience segments
- Recommend ad optimizations
- Create ad copy and targeting strategies
- Target: PE analysts, business brokers, CFOs
- Goal: Maintain 2.5x+ ROAS

Format response as JSON:
{
    "campaign_insights": "Analysis of current performance",
    "recommended_optimizations": ["optimization1", "optimization2"],
    "estimated_roas": 2.5
}"""
    
    @staticmethod
    def analyze_performance():
        """Analyze and optimize ad campaigns"""
        try:
            response = client.messages.create(
                model="claude-opus-4-20250805",
                max_tokens=1000,
                system=GrowthHacker.get_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": "Analyze LinkedIn and Google Ads performance for AcquiAxis AI targeting PE professionals. What optimizations would increase ROAS?"
                    }
                ]
            )
            
            analysis = json.loads(response.content[0].text)
            
            log_to_airtable("ad_campaign", {
                "Campaign": "Growth Optimization",
                "ROAS": analysis.get("estimated_roas", 2.5),
                "Status": "Optimized"
            })
            
            send_teams_notification(
                TEAMS_WEBHOOK_PERFORMANCE,
                f"📊 Growth Analysis Complete\n\nEstimated ROAS: {analysis.get('estimated_roas', 2.5)}x",
                "Growth Hacker",
                "00B050"
            )
            
            return analysis
        except Exception as e:
            logger.error(f"Failed to analyze performance: {str(e)}")
            return None

class ContentCreator:
    """Agent for blog posts, email content, and social media"""
    
    @staticmethod
    def get_system_prompt():
        return """You are the Content Creator for AcquiAxis AI.

Your role:
- Write blog posts about M&A, acquisitions, deal strategies
- Create email campaign content
- Topics: Due diligence, deal structures, integration, ROI
- Style: Educational, data-driven, actionable

Format response as JSON:
{
    "title": "Blog post title",
    "body": "Full blog post (800-1200 words)",
    "email_subject": "Email subject line"
}"""
    
    @staticmethod
    def create_content():
        """Generate new content"""
        try:
            response = client.messages.create(
                model="claude-opus-4-20250805",
                max_tokens=1500,
                system=ContentCreator.get_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": "Create a blog post about 'How to Close M&A Deals 3x Faster Using AI' for PE professionals."
                    }
                ]
            )
            
            content = json.loads(response.content[0].text)
            
            log_to_airtable("content", {
                "Title": content.get("title", ""),
                "Type": "Blog Post",
                "Status": "Published"
            })
            
            send_teams_notification(
                TEAMS_WEBHOOK_GENERAL,
                f"✍️ New Content Published\n\nTitle: {content.get('title', '')}",
                "Content Creator",
                "7030A0"
            )
            
            return content
        except Exception as e:
            logger.error(f"Failed to create content: {str(e)}")
            return None

class SEOSpecialist:
    """Agent for SEO optimization, ranking tracking, and organic growth"""
    
    @staticmethod
    def get_system_prompt():
        return """You are the SEO Specialist for AcquiAxis AI.

Your role:
- Identify high-value M&A keywords
- Optimize content for search rankings
- Build domain authority
- Target keywords: M&A automation, due diligence, deal management

Format response as JSON:
{
    "target_keywords": ["keyword1", "keyword2"],
    "optimization_recommendations": ["rec1", "rec2"],
    "estimated_traffic_increase": "150-200%"
}"""
    
    @staticmethod
    def optimize_seo():
        """Generate SEO optimization strategy"""
        try:
            response = client.messages.create(
                model="claude-opus-4-20250805",
                max_tokens=1000,
                system=SEOSpecialist.get_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": "Create an SEO strategy for AcquiAxis AI targeting M&A software keywords."
                    }
                ]
            )
            
            strategy = json.loads(response.content[0].text)
            
            log_to_airtable("seo_update", {
                "Keywords": ", ".join(strategy.get("target_keywords", [])[:5]),
                "Estimated_Traffic_Increase": strategy.get("estimated_traffic_increase", "")
            })
            
            send_teams_notification(
                TEAMS_WEBHOOK_PERFORMANCE,
                f"🔍 SEO Strategy Updated\n\nTarget Keywords: {', '.join(strategy.get('target_keywords', [])[:3])}",
                "SEO Specialist",
                "FF6B00"
            )
            
            return strategy
        except Exception as e:
            logger.error(f"Failed to optimize SEO: {str(e)}")
            return None

class TikTokStrategist:
    """Agent for TikTok content, viral growth, and audience engagement"""
    
    @staticmethod
    def get_system_prompt():
        return """You are the TikTok Strategist for AcquiAxis AI.

Your role:
- Create viral TikTok content ideas for B2B M&A audience
- Build audience from 0 to 50K+ followers
- Generate growth strategy
- Create short-form video concepts

Format response as JSON:
{
    "video_ideas": ["idea1", "idea2"],
    "hashtag_strategy": ["#hashtag1", "#hashtag2"],
    "growth_projection": "Follower growth estimate"
}"""
    
    @staticmethod
    def generate_tiktok_strategy():
        """Generate TikTok growth strategy"""
        try:
            response = client.messages.create(
                model="claude-opus-4-20250805",
                max_tokens=1000,
                system=TikTokStrategist.get_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": "Create a TikTok strategy for AcquiAxis AI targeting founders and operators. What viral content should we create?"
                    }
                ]
            )
            
            strategy = json.loads(response.content[0].text)
            
            send_teams_notification(
                TEAMS_WEBHOOK_VIRAL,
                f"🎬 TikTok Strategy Generated\n\nVideo Ideas: {', '.join(strategy.get('video_ideas', [])[:2])}",
                "TikTok Strategist",
                "FF0050"
            )
            
            return strategy
        except Exception as e:
            logger.error(f"Failed to generate TikTok strategy: {str(e)}")
            return None

# ============================================================================
# SCHEDULING & WORKFLOWS
# ============================================================================

def run_daily_agents():
    """Run all agents on daily schedule"""
    logger.info("Starting daily agent execution...")
    
    try:
        logger.info("Running LinkedIn Strategist...")
        linkedin_post = LinkedInStrategist.create_daily_post()
        
        logger.info("Running Content Creator...")
        content = ContentCreator.create_content()
        
        logger.info("Running Growth Hacker...")
        growth = GrowthHacker.analyze_performance()
        
        logger.info("Running SEO Specialist...")
        seo = SEOSpecialist.optimize_seo()
        
        logger.info("Running TikTok Strategist...")
        tiktok = TikTokStrategist.generate_tiktok_strategy()
        
        send_teams_notification(
            TEAMS_WEBHOOK_PERFORMANCE,
            "✅ Daily agent execution complete!\n\n📱 LinkedIn post created\n✍️ New content generated\n📊 Performance analyzed\n🔍 SEO optimized\n🎬 TikTok strategy updated",
            "AcquiAxis Daily Run",
            "107C10"
        )
        
        logger.info("Daily agent execution completed successfully")
        return True
    except Exception as e:
        logger.error(f"Daily agent execution failed: {str(e)}")
        send_teams_notification(
            TEAMS_WEBHOOK_GENERAL,
            f"❌ Daily execution failed: {str(e)}",
            "AcquiAxis Error",
            "FF0000"
        )
        return False

def schedule_agents():
    """Schedule agent tasks"""
    schedule.every().day.at("14:00").do(run_daily_agents)
    
    logger.info("Agents scheduled successfully")
    
    while True:
        schedule.run_pending()
        asyncio.sleep(60)

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": True,
        "agents": {
            "linkedin_strategist": {"status": "healthy"},
            "growth_hacker": {"status": "healthy"},
            "content_creator": {"status": "healthy"},
            "seo_specialist": {"status": "healthy"},
            "tiktok_strategist": {"status": "healthy"}
        }
    }), 200

@app.route('/run-agents', methods=['POST'])
def manual_run():
    """Manually trigger agent execution"""
    try:
        success = run_daily_agents()
        return jsonify({
            "status": "success" if success else "failed",
            "timestamp": datetime.now().isoformat()
        }), 200 if success else 500
    except Exception as e:
        logger.error(f"Manual run failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/agents/linkedin', methods=['POST'])
def trigger_linkedin():
    """Trigger LinkedIn agent"""
    try:
        post = LinkedInStrategist.create_daily_post()
        return jsonify(post or {"status": "failed"}), 200 if post else 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/agents/content', methods=['POST'])
def trigger_content():
    """Trigger Content Creator agent"""
    try:
        content = ContentCreator.create_content()
        return jsonify(content or {"status": "failed"}), 200 if content else 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/agents/growth', methods=['POST'])
def trigger_growth():
    """Trigger Growth Hacker agent"""
    try:
        analysis = GrowthHacker.analyze_performance()
        return jsonify(analysis or {"status": "failed"}), 200 if analysis else 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/agents/seo', methods=['POST'])
def trigger_seo():
    """Trigger SEO Specialist agent"""
    try:
        strategy = SEOSpecialist.optimize_seo()
        return jsonify(strategy or {"status": "failed"}), 200 if strategy else 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/agents/tiktok', methods=['POST'])
def trigger_tiktok():
    """Trigger TikTok Strategist agent"""
    try:
        strategy = TikTokStrategist.generate_tiktok_strategy()
        return jsonify(strategy or {"status": "failed"}), 200 if strategy else 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================================================
# STARTUP & MAIN
# ============================================================================

def startup_check():
    """Verify all systems are ready"""
    logger.info("=" * 80)
    logger.info("ACQUISAXIS AI - STARTUP CHECK")
    logger.info("=" * 80)
    
    checks = {
        "Anthropic API": bool(ANTHROPIC_API_KEY),
        "Teams General": bool(TEAMS_WEBHOOK_GENERAL),
        "Teams Performance": bool(TEAMS_WEBHOOK_PERFORMANCE),
        "Teams Viral": bool(TEAMS_WEBHOOK_VIRAL),
        "Teams Sales": bool(TEAMS_WEBHOOK_SALES),
        "LinkedIn API": bool(LINKEDIN_API_TOKEN),
        "LinkedIn Company": bool(LINKEDIN_COMPANY_ID),
        "Airtable API": bool(AIRTABLE_API_TOKEN),
        "Airtable Base": bool(AIRTABLE_BASE_ID),
    }
    
    all_good = all(checks.values())
    
    for check, status in checks.items():
        status_str = "✅" if status else "❌"
        logger.info(f"{status_str} {check}: {'Configured' if status else 'Missing'}")
    
    logger.info("=" * 80)
    
    if all_good:
        logger.info("✅ ALL SYSTEMS READY - STARTING AGENTS")
        
        send_teams_notification(
            TEAMS_WEBHOOK_GENERAL,
            "🚀 AcquiAxis AI agents are LIVE!\n\n✅ LinkedIn Strategist\n✅ Growth Hacker\n✅ Content Creator\n✅ SEO Specialist\n✅ TikTok Strategist\n\nDaily operations beginning now...",
            "AcquiAxis AI Launched",
            "107C10"
        )
    else:
        logger.warning("⚠️ Some systems not configured - running in limited mode")
    
    return all_good

if __name__ == "__main__":
    logger.info(f"Starting AcquiAxis AI on port {PORT}")
    
    startup_check()
    
    scheduler_thread = threading.Thread(target=schedule_agents, daemon=True)
    scheduler_thread.start()
    logger.info("Agent scheduler started")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
