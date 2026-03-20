"""
Database Integration for RTL-Gen AI
Supports PostgreSQL (production) and SQLite (development)
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Try to import SQLAlchemy, gracefully degrade if not available
try:
    from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, JSON, Float, Boolean
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.dialects.postgresql import UUID
    import uuid
    
    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()

    class Design(Base):
        """Stored design in database"""
        __tablename__ = 'designs'
        
        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String(100), nullable=True)
        prompt = Column(Text, nullable=False)
        rtl_code = Column(Text, nullable=False)
        testbench_code = Column(Text, nullable=True)
        provider = Column(String(50), nullable=False)
        model = Column(String(50), nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        metadata_json = Column(JSON, nullable=True)
        waveform_path = Column(String(500), nullable=True)
        synthesis_path = Column(String(500), nullable=True)
        tags = Column(String(500), nullable=True)
        is_public = Column(Boolean, default=False)
        
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger.warning("SQLAlchemy not available - database features disabled")
    Base = None


class DesignDatabase:
    """Database manager for designs"""
    
    def __init__(self, database_url: Optional[str] = None, use_db: bool = True):
        """
        Initialize database connection
        
        Args:
            database_url: Connection string. If None, uses env var or SQLite
            use_db: Whether to enable database features
        """
        self.use_db = use_db and SQLALCHEMY_AVAILABLE
        
        if not self.use_db:
            logger.info("Database features disabled")
            return
        
        if database_url is None:
            # Use environment variable or default to SQLite
            database_url = os.getenv('DATABASE_URL', 'sqlite:///./rtl-gen.db')
        
        try:
            self.engine = create_engine(database_url)
            Base.metadata.create_all(self.engine)
            self.SessionLocal = sessionmaker(bind=self.engine)
            logger.info(f"Database initialized: {database_url.split('@')[0]}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.use_db = False
    
    def save_design(self, 
                   prompt: str, 
                   rtl_code: str, 
                   testbench_code: Optional[str] = None,
                   provider: str = 'mock',
                   model: Optional[str] = None,
                   metadata: Optional[Dict] = None,
                   waveform_path: Optional[str] = None,
                   synthesis_path: Optional[str] = None,
                   tags: Optional[List[str]] = None,
                   user_id: Optional[str] = None) -> Optional[str]:
        """Save design to database"""
        if not self.use_db:
            return None
        
        try:
            session = self.SessionLocal()
            design = Design(
                prompt=prompt,
                rtl_code=rtl_code,
                testbench_code=testbench_code,
                provider=provider,
                model=model,
                metadata_json=metadata or {},
                waveform_path=waveform_path,
                synthesis_path=synthesis_path,
                tags=','.join(tags) if tags else None,
                user_id=user_id
            )
            session.add(design)
            session.commit()
            design_id = design.id
            session.close()
            logger.info(f"Design saved: {design_id}")
            return design_id
        except Exception as e:
            logger.error(f"Failed to save design: {e}")
            return None
    
    def get_design(self, design_id: str) -> Optional[Dict]:
        """Retrieve design by ID"""
        if not self.use_db:
            return None
        
        try:
            session = self.SessionLocal()
            design = session.query(Design).filter_by(id=design_id).first()
            session.close()
            
            if design:
                return {
                    'id': str(design.id),
                    'prompt': design.prompt,
                    'rtl_code': design.rtl_code,
                    'testbench_code': design.testbench_code,
                    'provider': design.provider,
                    'model': design.model,
                    'created_at': design.created_at.isoformat(),
                    'updated_at': design.updated_at.isoformat(),
                    'metadata': design.metadata_json or {},
                    'waveform_path': design.waveform_path,
                    'synthesis_path': design.synthesis_path,
                    'tags': design.tags.split(',') if design.tags else [],
                    'is_public': design.is_public
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get design: {e}")
            return None
    
    def search_designs(self, 
                      query: str = "", 
                      provider: Optional[str] = None,
                      tags: Optional[List[str]] = None,
                      user_id: Optional[str] = None,
                      limit: int = 50,
                      offset: int = 0) -> List[Dict]:
        """Search designs by criteria"""
        if not self.use_db:
            return []
        
        try:
            session = self.SessionLocal()
            q = session.query(Design)
            
            if query:
                q = q.filter(
                    (Design.prompt.contains(query)) | 
                    (Design.rtl_code.contains(query))
                )
            
            if provider:
                q = q.filter_by(provider=provider)
            
            if user_id:
                q = q.filter_by(user_id=user_id)
            
            if tags:
                for tag in tags:
                    q = q.filter(Design.tags.contains(tag))
            
            designs = q.order_by(Design.created_at.desc())\
                       .offset(offset)\
                       .limit(limit).all()
            
            result = [{
                'id': str(d.id),
                'prompt': d.prompt[:100] + '...' if len(d.prompt) > 100 else d.prompt,
                'provider': d.provider,
                'created_at': d.created_at.isoformat(),
                'tags': d.tags.split(',') if d.tags else [],
                'is_public': d.is_public
            } for d in designs]
            
            session.close()
            return result
        except Exception as e:
            logger.error(f"Failed to search designs: {e}")
            return []
    
    def list_public_designs(self, limit: int = 20) -> List[Dict]:
        """Get public designs for sharing"""
        if not self.use_db:
            return []
        
        return self.search_designs(limit=limit)
    
    def update_design(self, design_id: str, **kwargs) -> bool:
        """Update design fields"""
        if not self.use_db:
            return False
        
        try:
            session = self.SessionLocal()
            design = session.query(Design).filter_by(id=design_id).first()
            
            if design:
                for key, value in kwargs.items():
                    if hasattr(design, key):
                        setattr(design, key, value)
                
                session.commit()
                session.close()
                return True
            
            session.close()
            return False
        except Exception as e:
            logger.error(f"Failed to update design: {e}")
            return False
    
    def delete_design(self, design_id: str) -> bool:
        """Delete a design"""
        if not self.use_db:
            return False
        
        try:
            session = self.SessionLocal()
            design = session.query(Design).filter_by(id=design_id).first()
            
            if design:
                session.delete(design)
                session.commit()
                session.close()
                return True
            
            session.close()
            return False
        except Exception as e:
            logger.error(f"Failed to delete design: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.use_db:
            return {}
        
        try:
            session = self.SessionLocal()
            total_designs = session.query(Design).count()
            providers = session.query(Design.provider).distinct().all()
            recent = session.query(Design).order_by(Design.created_at.desc()).limit(5).all()
            
            session.close()
            
            return {
                'total_designs': total_designs,
                'providers': [p[0] for p in providers],
                'recent_designs': len(recent)
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


# Streamlit integration functions
def add_database_integration(db: DesignDatabase):
    """Add database UI components to Streamlit"""
    import streamlit as st
    
    st.sidebar.subheader("💾 Design Storage")
    
    # Save current design
    if st.session_state.get('generated_code'):
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("💾 Save Design", use_container_width=True):
                design_id = db.save_design(
                    prompt=st.session_state.get('prompt', 'Untitled'),
                    rtl_code=st.session_state.generated_code,
                    testbench_code=st.session_state.get('testbench_code'),
                    provider=st.session_state.get('provider', 'mock'),
                    tags=['design']
                )
                if design_id:
                    st.sidebar.success(f"✅ Saved! ID: {design_id[:8]}")
                    st.session_state.current_design_id = design_id
        
        with col2:
            if st.button("🌐 Share", use_container_width=True):
                if hasattr(st.session_state, 'current_design_id'):
                    db.update_design(st.session_state.current_design_id, is_public=True)
                    st.sidebar.info("✅ Design is now public!")
    
    # Load previous designs
    with st.sidebar.expander("📚 Load Saved Design", expanded=False):
        designs = db.search_designs(limit=10)
        if designs:
            selected = st.selectbox(
                "Select design to load",
                options=designs,
                format_func=lambda x: f"{x['created_at'][:10]} - {x['prompt'][:30]}"
            )
            
            if st.button("🔄 Load Selected"):
                loaded = db.get_design(selected['id'])
                if loaded:
                    st.session_state.generated_code = loaded['rtl_code']
                    st.session_state.testbench_code = loaded['testbench_code']
                    st.rerun()
        else:
            st.info("No saved designs yet")


def add_analytics_view(db: DesignDatabase):
    """Add analytics dashboard"""
    import streamlit as st
    
    stats = db.get_stats()
    
    if stats:
        st.subheader("📊 Analytics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Designs", stats.get('total_designs', 0))
        with col2:
            st.metric("Providers Used", len(stats.get('providers', [])))
        with col3:
            st.metric("Recent Designs", stats.get('recent_designs', 0))
