"""
Database Routers for Read/Write Splitting
==========================================
Handles routing reads to replicas and writes to primary database.
Enable this when you add read replicas for scaling.
"""

import random


class PrimaryReplicaRouter:
    """
    Routes database reads to replicas and writes to primary.
    
    This allows horizontal scaling by distributing read load across
    multiple replica databases while ensuring all writes go to primary.
    
    Usage:
        1. Configure replica databases in settings.py
        2. Add to DATABASE_ROUTERS setting:
           DATABASE_ROUTERS = ['estateApp.db_routers.PrimaryReplicaRouter']
    """
    
    # List of replica database aliases
    replicas = ['replica']  # Add more: ['replica1', 'replica2', ...]
    
    def db_for_read(self, model, **hints):
        """
        Route reads to a random replica for load distribution.
        Falls back to default if no replicas available.
        """
        # Check if replicas are configured
        from django.conf import settings
        available_replicas = [
            r for r in self.replicas 
            if r in settings.DATABASES
        ]
        
        if available_replicas:
            return random.choice(available_replicas)
        return 'default'
    
    def db_for_write(self, model, **hints):
        """
        Always route writes to the primary database.
        """
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between objects from any database.
        """
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Only run migrations on the primary database.
        Replicas should replicate from primary.
        """
        return db == 'default'


class TenantShardRouter:
    """
    Routes queries to tenant-specific database shards.
    
    For massive scale (1M+ users), data is partitioned by company_id
    across multiple database servers (shards).
    
    Usage:
        1. Configure shard databases in settings.py:
           DATABASES = {
               'default': {...},  # Metadata DB
               'shard_0': {...},
               'shard_1': {...},
               ...
           }
        2. Add to DATABASE_ROUTERS:
           DATABASE_ROUTERS = ['estateApp.db_routers.TenantShardRouter']
    """
    
    # Models that should be sharded by company
    SHARDED_MODELS = [
        'client', 'marketer', 'estate', 'transaction',
        'allocation', 'payment', 'chat', 'message',
    ]
    
    # Models that stay in the default (metadata) database
    GLOBAL_MODELS = [
        'company', 'customuser', 'subscriptionplan', 'auditlog',
    ]
    
    # Number of shards (configure based on your setup)
    SHARD_COUNT = 10
    
    def _get_shard(self, company_id):
        """
        Determine which shard holds data for a company.
        Uses modulo hashing for even distribution.
        """
        if company_id is None:
            return 'default'
        shard_num = company_id % self.SHARD_COUNT
        return f'shard_{shard_num}'
    
    def _get_company_id(self, model, **hints):
        """
        Extract company_id from model instance or hints.
        """
        # Check hints first
        if 'company_id' in hints:
            return hints['company_id']
        
        # Check instance
        instance = hints.get('instance')
        if instance:
            # Direct company_id attribute
            if hasattr(instance, 'company_id'):
                return instance.company_id
            # Through company relation
            if hasattr(instance, 'company') and instance.company:
                return instance.company.id
        
        # Try thread-local company context
        try:
            from estateApp.middleware import get_current_company
            company = get_current_company()
            if company:
                return company.id
        except ImportError:
            pass
        
        return None
    
    def db_for_read(self, model, **hints):
        """Route reads to appropriate shard."""
        model_name = model._meta.model_name.lower()
        
        # Global models stay in default DB
        if model_name in self.GLOBAL_MODELS:
            return 'default'
        
        # Sharded models go to their shard
        if model_name in self.SHARDED_MODELS:
            company_id = self._get_company_id(model, **hints)
            return self._get_shard(company_id)
        
        return 'default'
    
    def db_for_write(self, model, **hints):
        """Route writes to appropriate shard."""
        return self.db_for_read(model, **hints)
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Only allow relations within the same shard.
        Cross-shard relations require application-level joins.
        """
        # Get databases for both objects
        db1 = self.db_for_read(type(obj1), instance=obj1)
        db2 = self.db_for_read(type(obj2), instance=obj2)
        
        # Allow if same database
        if db1 == db2:
            return True
        
        # Allow global <-> shard relations
        if db1 == 'default' or db2 == 'default':
            return True
        
        return False
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Run migrations on all shards and default.
        """
        from django.conf import settings
        
        # Check if this is a shard database
        if db.startswith('shard_') or db == 'default':
            return True
        
        return False


class HybridRouter:
    """
    Combines read/write splitting with tenant sharding.
    
    For enterprise scale:
    - Reads distributed across replicas within each shard
    - Writes go to primary of each shard
    - Tenants are distributed across shards
    """
    
    primary_replica_router = PrimaryReplicaRouter()
    shard_router = TenantShardRouter()
    
    def db_for_read(self, model, **hints):
        """First determine shard, then choose replica within shard."""
        shard = self.shard_router.db_for_read(model, **hints)
        
        # If it's a shard, try to use a replica
        if shard.startswith('shard_'):
            replica = f'{shard}_replica'
            from django.conf import settings
            if replica in settings.DATABASES:
                return replica
        
        return shard
    
    def db_for_write(self, model, **hints):
        """Writes always go to primary of the shard."""
        return self.shard_router.db_for_write(model, **hints)
    
    def allow_relation(self, obj1, obj2, **hints):
        return self.shard_router.allow_relation(obj1, obj2, **hints)
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return self.shard_router.allow_migrate(db, app_label, model_name, **hints)
