@description('Azure region for the resource.')
param location string

@description('Name of the Azure AI Hub (Machine Learning workspace of kind Hub).')
param aiHubName string

@description('Name of the existing Azure AI Services account to connect.')
param aiServicesName string

@description('Resource ID of the Azure AI Services account.')
param aiServicesResourceId string

@description('Endpoint of the Azure AI Services account.')
param aiServicesEndpoint string

@description('Resource ID of the storage account.')
param storageAccountResourceId string

@description('Resource ID of the Key Vault.')
param keyVaultResourceId string

@description('Resource ID of the Azure AI Search service.')
param searchServiceResourceId string

@description('Endpoint of the Azure AI Search service.')
param searchServiceEndpoint string

@description('Resource tags.')
param tags object = {}

resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: aiHubName
  location: location
  tags: tags
  kind: 'Hub'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: aiHubName
    storageAccount: storageAccountResourceId
    keyVault: keyVaultResourceId
  }
}

resource aiServicesConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-04-01' = {
  parent: aiHub
  name: 'aoai-connection'
  properties: {
    category: 'AzureOpenAI'
    target: aiServicesEndpoint
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: listKeys(aiServicesResourceId, '2024-04-01-preview').key1
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: aiServicesResourceId
    }
  }
}

resource searchConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-04-01' = {
  parent: aiHub
  name: 'search-connection'
  properties: {
    category: 'CognitiveSearch'
    target: searchServiceEndpoint
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: listAdminKeys(searchServiceResourceId, '2024-03-01-preview').primaryKey
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchServiceResourceId
    }
  }
}

// Grant the AI Hub's managed identity access to AI Services
resource aiServicesRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiHub.id, aiServicesResourceId, 'CognitiveServicesOpenAIContributor')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a001fd3d-188f-4b5d-821b-7da978bf7442')
    principalId: aiHub.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output name string = aiHub.name
output resourceId string = aiHub.id
output principalId string = aiHub.identity.principalId
output aiServicesConnectionName string = aiServicesConnection.name
output searchConnectionName string = searchConnection.name
