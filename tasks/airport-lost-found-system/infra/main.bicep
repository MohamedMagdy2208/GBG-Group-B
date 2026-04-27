@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short lowercase prefix used for resource names.')
param namePrefix string

@description('Backend container image, for example myregistry.azurecr.io/airport-api:latest.')
param backendImage string

@description('Frontend container image, built with VITE_API_URL pointing at the backend URL.')
param frontendImage string

@description('Optional private registry server, for example myregistry.azurecr.io.')
param containerRegistryServer string = ''

@description('Optional private registry username.')
param containerRegistryUsername string = ''

@secure()
@description('Optional private registry password.')
param containerRegistryPassword string = ''

@secure()
param postgresAdminPassword string

@secure()
param jwtSecret string

@secure()
param azureOpenAIApiKey string = ''

@secure()
param azureStorageConnectionString string = ''

@secure()
param azureVisionKey string = ''

@secure()
param azureSearchKey string = ''

@secure()
param azureCommunicationConnectionString string = ''

@secure()
param azureSpeechKey string = ''

param postgresAdminLogin string = 'airportadmin'
param databaseName string = 'airport_lost_found'
param useAzureServices bool = true
param azureOpenAIEndpoint string = ''
param azureOpenAIChatDeployment string = ''
param azureOpenAIEmbeddingDeployment string = ''
param azureOpenAIApiVersion string = '2024-10-21'
param azureVisionEndpoint string = ''
param azureSearchIndexName string = 'airport-lost-found'
param azureSearchVectorDimensions int = 1536
param azureCommunicationEmailSender string = 'DoNotReply@airport.example'
param azureCommunicationSmsSender string = '+10000000000'
param azureSpeechRegion string = ''
param azureSpeechEndpoint string = ''
param azureSpeechVoiceEn string = 'en-US-JennyNeural'
param azureSpeechVoiceAr string = 'ar-EG-SalmaNeural'
param azureCosmosGremlinEndpoint string = ''
@secure()
param azureCosmosGremlinKey string = ''
param azureCosmosGremlinDatabase string = 'airport-lost-found'
param azureCosmosGremlinGraph string = 'operations-graph'
param voiceFeaturesEnabled bool = true
param voiceProvider string = 'browser'
param qrLabelBaseUrl string = ''
param fraudHighRiskThreshold int = 70
param claimVerificationExpiryHours int = 72
param graphRagProvider string = 'postgres'
param graphRagContextTtlSeconds int = 300

var normalizedPrefix = toLower(namePrefix)
var logAnalyticsName = '${normalizedPrefix}-logs'
var appInsightsName = '${normalizedPrefix}-appi'
var appEnvironmentName = '${normalizedPrefix}-env'
var keyVaultName = take(replace('${normalizedPrefix}kv', '-', ''), 24)
var storageName = take(replace('${normalizedPrefix}store', '-', ''), 24)
var searchName = '${normalizedPrefix}-search'
var postgresName = '${normalizedPrefix}-pg'
var redisName = '${normalizedPrefix}-redis'
var backendName = '${normalizedPrefix}-api'
var frontendName = '${normalizedPrefix}-web'
var backendIdentityName = '${normalizedPrefix}-api-id'
var databaseUrl = 'postgresql+psycopg://${postgresAdminLogin}:${postgresAdminPassword}@${postgresName}.postgres.database.azure.com:5432/${databaseName}?sslmode=require'
var registrySecrets = empty(containerRegistryServer) ? [] : [
  {
    name: 'registry-password'
    value: containerRegistryPassword
  }
]
var registryConfig = empty(containerRegistryServer) ? [] : [
  {
    server: containerRegistryServer
    username: containerRegistryUsername
    passwordSecretRef: 'registry-password'
  }
]

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
  }
}

resource backendIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: backendIdentityName
  location: location
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'lost-found'
  properties: {
    publicAccess: 'None'
  }
}

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchName
  location: location
  sku: {
    name: 'basic'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: postgresName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    version: '16'
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
    }
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgres
  name: databaseName
}

resource postgresAllowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisName
  location: location
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
  }
}

resource appEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: appEnvironmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DATABASE-URL'
  properties: {
    value: databaseUrl
  }
}

resource jwtSecretValue 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'JWT-SECRET'
  properties: {
    value: jwtSecret
  }
}

resource openAIKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AZURE-OPENAI-API-KEY'
  properties: {
    value: azureOpenAIApiKey
  }
}

resource storageConnectionSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AZURE-STORAGE-CONNECTION-STRING'
  properties: {
    value: empty(azureStorageConnectionString) ? 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net' : azureStorageConnectionString
  }
}

resource visionKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AZURE-AI-VISION-KEY'
  properties: {
    value: azureVisionKey
  }
}

resource searchKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AZURE-SEARCH-KEY'
  properties: {
    value: empty(azureSearchKey) ? listAdminKeys(search.id, search.apiVersion).primaryKey : azureSearchKey
  }
}

resource communicationSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AZURE-COMMUNICATION-CONNECTION-STRING'
  properties: {
    value: azureCommunicationConnectionString
  }
}

resource speechKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AZURE-SPEECH-KEY'
  properties: {
    value: azureSpeechKey
  }
}

resource cosmosGremlinKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AZURE-COSMOS-GREMLIN-KEY'
  properties: {
    value: azureCosmosGremlinKey
  }
}

resource appInsightsSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'APPLICATIONINSIGHTS-CONNECTION-STRING'
  properties: {
    value: appInsights.properties.ConnectionString
  }
}

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: backendName
  location: location
  dependsOn: [
    keyVaultSecretsUser
  ]
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${backendIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: appEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      secrets: concat([
        {
          name: 'database-url'
          keyVaultUrl: databaseUrlSecret.properties.secretUri
          identity: backendIdentity.id
        }
        {
          name: 'jwt-secret'
          keyVaultUrl: jwtSecretValue.properties.secretUri
          identity: backendIdentity.id
        }
        {
          name: 'azure-openai-api-key'
          keyVaultUrl: openAIKeySecret.properties.secretUri
          identity: backendIdentity.id
        }
        {
          name: 'azure-storage-connection-string'
          keyVaultUrl: storageConnectionSecret.properties.secretUri
          identity: backendIdentity.id
        }
        {
          name: 'azure-ai-vision-key'
          keyVaultUrl: visionKeySecret.properties.secretUri
          identity: backendIdentity.id
        }
        {
          name: 'azure-search-key'
          keyVaultUrl: searchKeySecret.properties.secretUri
          identity: backendIdentity.id
        }
        {
          name: 'azure-communication-connection-string'
          keyVaultUrl: communicationSecret.properties.secretUri
          identity: backendIdentity.id
        }
        {
          name: 'azure-speech-key'
          keyVaultUrl: speechKeySecret.properties.secretUri
          identity: backendIdentity.id
        }
        {
          name: 'azure-cosmos-gremlin-key'
          keyVaultUrl: cosmosGremlinKeySecret.properties.secretUri
          identity: backendIdentity.id
        }
        {
          name: 'applicationinsights-connection-string'
          keyVaultUrl: appInsightsSecret.properties.secretUri
          identity: backendIdentity.id
        }
      ], registrySecrets)
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'JWT_SECRET'
              secretRef: 'jwt-secret'
            }
            {
              name: 'USE_AZURE_SERVICES'
              value: string(useAzureServices)
            }
            {
              name: 'AZURE_KEY_VAULT_URL'
              value: keyVault.properties.vaultUri
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAIEndpoint
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-api-key'
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: azureOpenAIApiVersion
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
              value: azureOpenAIChatDeployment
            }
            {
              name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
              value: azureOpenAIEmbeddingDeployment
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT_NAME'
              value: storage.name
            }
            {
              name: 'AZURE_STORAGE_CONTAINER_NAME'
              value: blobContainer.name
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'azure-storage-connection-string'
            }
            {
              name: 'AZURE_AI_VISION_ENDPOINT'
              value: azureVisionEndpoint
            }
            {
              name: 'AZURE_AI_VISION_KEY'
              secretRef: 'azure-ai-vision-key'
            }
            {
              name: 'AZURE_SEARCH_ENDPOINT'
              value: 'https://${search.name}.search.windows.net'
            }
            {
              name: 'AZURE_SEARCH_KEY'
              secretRef: 'azure-search-key'
            }
            {
              name: 'AZURE_SEARCH_INDEX_NAME'
              value: azureSearchIndexName
            }
            {
              name: 'AZURE_SEARCH_VECTOR_DIMENSIONS'
              value: string(azureSearchVectorDimensions)
            }
            {
              name: 'AZURE_COMMUNICATION_CONNECTION_STRING'
              secretRef: 'azure-communication-connection-string'
            }
            {
              name: 'AZURE_COMMUNICATION_EMAIL_SENDER'
              value: azureCommunicationEmailSender
            }
            {
              name: 'AZURE_COMMUNICATION_SMS_SENDER'
              value: azureCommunicationSmsSender
            }
            {
              name: 'AZURE_SPEECH_KEY'
              secretRef: 'azure-speech-key'
            }
            {
              name: 'AZURE_SPEECH_REGION'
              value: azureSpeechRegion
            }
            {
              name: 'AZURE_SPEECH_ENDPOINT'
              value: azureSpeechEndpoint
            }
            {
              name: 'AZURE_SPEECH_VOICE_EN'
              value: azureSpeechVoiceEn
            }
            {
              name: 'AZURE_SPEECH_VOICE_AR'
              value: azureSpeechVoiceAr
            }
            {
              name: 'VOICE_FEATURES_ENABLED'
              value: string(voiceFeaturesEnabled)
            }
            {
              name: 'VOICE_PROVIDER'
              value: voiceProvider
            }
            {
              name: 'QR_LABEL_BASE_URL'
              value: qrLabelBaseUrl
            }
            {
              name: 'FRAUD_HIGH_RISK_THRESHOLD'
              value: string(fraudHighRiskThreshold)
            }
            {
              name: 'CLAIM_VERIFICATION_EXPIRY_HOURS'
              value: string(claimVerificationExpiryHours)
            }
            {
              name: 'GRAPH_RAG_ENABLED'
              value: 'true'
            }
            {
              name: 'GRAPH_RAG_PROVIDER'
              value: graphRagProvider
            }
            {
              name: 'GRAPH_RAG_CONTEXT_TTL_SECONDS'
              value: string(graphRagContextTtlSeconds)
            }
            {
              name: 'AZURE_COSMOS_GREMLIN_ENDPOINT'
              value: azureCosmosGremlinEndpoint
            }
            {
              name: 'AZURE_COSMOS_GREMLIN_KEY'
              secretRef: 'azure-cosmos-gremlin-key'
            }
            {
              name: 'AZURE_COSMOS_GREMLIN_DATABASE'
              value: azureCosmosGremlinDatabase
            }
            {
              name: 'AZURE_COSMOS_GREMLIN_GRAPH'
              value: azureCosmosGremlinGraph
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'applicationinsights-connection-string'
            }
            {
              name: 'REDIS_URL'
              value: 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0'
            }
            {
              name: 'RUN_MIGRATIONS_ON_STARTUP'
              value: 'true'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
        {
          name: 'worker'
          image: backendImage
          command: [
            'python'
            '-m'
            'app.scripts.worker'
          ]
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'JWT_SECRET'
              secretRef: 'jwt-secret'
            }
            {
              name: 'USE_AZURE_SERVICES'
              value: string(useAzureServices)
            }
            {
              name: 'AZURE_KEY_VAULT_URL'
              value: keyVault.properties.vaultUri
            }
            {
              name: 'REDIS_URL'
              value: 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'applicationinsights-connection-string'
            }
            {
              name: 'RUN_MIGRATIONS_ON_STARTUP'
              value: 'false'
            }
            {
              name: 'WORKER_POLL_INTERVAL_SECONDS'
              value: '5'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: frontendName
  location: location
  properties: {
    managedEnvironmentId: appEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
      }
      secrets: registrySecrets
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

resource keyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, backendIdentity.id, 'Key Vault Secrets User')
  scope: keyVault
  properties: {
    principalId: backendIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
  }
}

output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output keyVaultUrl string = keyVault.properties.vaultUri
output searchEndpoint string = 'https://${search.name}.search.windows.net'
