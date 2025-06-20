// MongoDB initialization script
// This script runs when the MongoDB container starts for the first time

// Switch to the nexus_db database
db = db.getSiblingDB('nexus_db');

// Create users collection with validation schema
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['email', 'hashed_password', 'full_name', 'role', 'is_active', 'created_at'],
      properties: {
        email: {
          bsonType: 'string',
          pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$',
          description: 'must be a valid email address'
        },
        hashed_password: {
          bsonType: 'string',
          description: 'must be a string and is required'
        },
        full_name: {
          bsonType: 'string',
          minLength: 1,
          description: 'must be a string and is required'
        },
        role: {
          enum: ['admin', 'user', 'moderator'],
          description: 'must be one of the allowed roles'
        },
        is_active: {
          bsonType: 'bool',
          description: 'must be a boolean and is required'
        },
        created_at: {
          bsonType: 'date',
          description: 'must be a date and is required'
        },
        last_login: {
          bsonType: ['date', 'null'],
          description: 'must be a date or null'
        }
      }
    }
  }
});

// Create indexes for users collection
db.users.createIndex({ 'email': 1 }, { unique: true });
db.users.createIndex({ 'role': 1 });
db.users.createIndex({ 'is_active': 1 });
db.users.createIndex({ 'created_at': 1 });

// Create audit_logs collection for tracking user actions
db.createCollection('audit_logs', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['user_id', 'action', 'timestamp', 'ip_address'],
      properties: {
        user_id: {
          bsonType: 'objectId',
          description: 'must be an ObjectId and is required'
        },
        action: {
          bsonType: 'string',
          description: 'must be a string and is required'
        },
        timestamp: {
          bsonType: 'date',
          description: 'must be a date and is required'
        },
        ip_address: {
          bsonType: 'string',
          description: 'must be a string and is required'
        },
        details: {
          bsonType: 'object',
          description: 'additional details about the action'
        }
      }
    }
  }
});

// Create indexes for audit_logs collection
db.audit_logs.createIndex({ 'user_id': 1 });
db.audit_logs.createIndex({ 'timestamp': 1 });
db.audit_logs.createIndex({ 'action': 1 });

// Create sessions collection for managing user sessions
db.createCollection('sessions', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['user_id', 'token_hash', 'created_at', 'expires_at', 'is_active'],
      properties: {
        user_id: {
          bsonType: 'objectId',
          description: 'must be an ObjectId and is required'
        },
        token_hash: {
          bsonType: 'string',
          description: 'must be a string and is required'
        },
        created_at: {
          bsonType: 'date',
          description: 'must be a date and is required'
        },
        expires_at: {
          bsonType: 'date',
          description: 'must be a date and is required'
        },
        is_active: {
          bsonType: 'bool',
          description: 'must be a boolean and is required'
        },
        ip_address: {
          bsonType: 'string',
          description: 'IP address of the session'
        },
        user_agent: {
          bsonType: 'string',
          description: 'User agent of the session'
        }
      }
    }
  }
});

// Create indexes for sessions collection
db.sessions.createIndex({ 'user_id': 1 });
db.sessions.createIndex({ 'token_hash': 1 }, { unique: true });
db.sessions.createIndex({ 'expires_at': 1 }, { expireAfterSeconds: 0 });
db.sessions.createIndex({ 'is_active': 1 });

// Create API keys collection for service-to-service authentication
db.createCollection('api_keys', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'key_hash', 'permissions', 'created_at', 'is_active'],
      properties: {
        name: {
          bsonType: 'string',
          description: 'must be a string and is required'
        },
        key_hash: {
          bsonType: 'string',
          description: 'must be a string and is required'
        },
        permissions: {
          bsonType: 'array',
          items: {
            bsonType: 'string'
          },
          description: 'must be an array of permission strings'
        },
        created_at: {
          bsonType: 'date',
          description: 'must be a date and is required'
        },
        expires_at: {
          bsonType: ['date', 'null'],
          description: 'must be a date or null'
        },
        is_active: {
          bsonType: 'bool',
          description: 'must be a boolean and is required'
        },
        created_by: {
          bsonType: 'objectId',
          description: 'user who created this API key'
        },
        last_used: {
          bsonType: ['date', 'null'],
          description: 'last time this API key was used'
        }
      }
    }
  }
});

// Create indexes for api_keys collection
db.api_keys.createIndex({ 'key_hash': 1 }, { unique: true });
db.api_keys.createIndex({ 'is_active': 1 });
db.api_keys.createIndex({ 'created_by': 1 });
db.api_keys.createIndex({ 'expires_at': 1 });

// Insert default admin user (password: admin123)
// Note: In production, this should be changed immediately
db.users.insertOne({
  email: 'admin@nexus.local',
  hashed_password: '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJgusgqHu', // admin123
  full_name: 'System Administrator',
  role: 'admin',
  is_active: true,
  created_at: new Date(),
  last_login: null
});

// Insert sample user (password: user123)
db.users.insertOne({
  email: 'user@nexus.local',
  hashed_password: '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', // user123
  full_name: 'Sample User',
  role: 'user',
  is_active: true,
  created_at: new Date(),
  last_login: null
});

print('Database initialization completed successfully!');
print('Default users created:');
print('  Admin: admin@nexus.local / admin123');
print('  User: user@nexus.local / user123');
print('Please change these default passwords in production!');
