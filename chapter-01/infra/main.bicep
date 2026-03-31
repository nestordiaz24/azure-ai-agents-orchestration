targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment (e.g. dev, test, prod).')
param environmentName string

@minLength(1)
@description('Primary location for all resources.')
param location string

@description('Name of the resource group. Defaults to rg-<environmentName>.')
param resourceGroupName string = ''

@description('Name of the Azure AI Hub. Defaults to hub-<environmentName>.')
param aiHubName string = ''

@description('Name of the Azure AI Project. Defaults to project-<environmentName>.')
param aiProjectName string = ''

@description('Name of the Azure AI Services account.')
param aiServicesName string = ''

@description('Model to deploy (e.g., gpt-4o).')
param modelName string = 'gpt-4o'

@description('Model version.')
param modelVersion string = '2024-11-20'

@description('Model deployment SKU capacity (TPM in thousands).')
param modelCapacity int = 30

@description('Name of the Azure AI Search service. Leave empty to skip.')
param searchServiceName string = ''

@description('Azure AI Search SKU.')
@allowed(['free', 'basic', 'standard', 'standard2', 'standard3'])
param searchServiceSku string = 'basic'

@description('Name of the search index to create.')
param searchIndexName string = 'documents'

@description('Name of the Azure Storage account used by the AI Hub.')
param storageAccountName string = ''

@description('Name of the Azure Key Vault used by the AI Hub.')
param keyVaultName string = ''

var abbrs = {
  resourcesResourceGroup: 'rg-'
  cognitiveServicesAccounts: 'aoai-'
  machineLearningServicesWorkspaces: 'hub-'
  machineLearningServicesProjects: 'project-'
  searchSearchServices: 'search-'
  storageStorageAccounts: 'st'
  keyVaultVaults: 'kv-'
}

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

var resolvedResourceGroupName = !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroup}${environmentName}'
var resolvedAiHubName = !empty(aiHubName) ? aiHubName : '${abbrs.machineLearningServicesWorkspaces}${resourceToken}'
var resolvedAiProjectName = !empty(aiProjectName) ? aiProjectName : '${abbrs.machineLearningServicesProjects}${resourceToken}'
var resolvedAiServicesName = !empty(aiServicesName) ? aiServicesName : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
var resolvedSearchServiceName = !empty(searchServiceName) ? searchServiceName : '${abbrs.searchSearchServices}${resourceToken}'
var resolvedStorageAccountName = !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
var resolvedKeyVaultName = !empty(keyVaultName) ? keyVaultName : '${abbrs.keyVaultVaults}${resourceToken}'

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: resolvedResourceGroupName
  location: location
  tags: {
    'azd-env-name': environmentName
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    location: location
    storageAccountName: resolvedStorageAccountName
    tags: { 'azd-env-name': environmentName }
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  scope: rg
  params: {
    location: location
    keyVaultName: resolvedKeyVaultName
    tags: { 'azd-env-name': environmentName }
  }
}

module aiServices 'modules/ai-services.bicep' = {
  name: 'aiServices'
  scope: rg
  params: {
    location: location
    aiServicesName: resolvedAiServicesName
    modelName: modelName
    modelVersion: modelVersion
    modelCapacity: modelCapacity
    tags: { 'azd-env-name': environmentName }
  }
}

module searchService 'modules/search-service.bicep' = {
  name: 'searchService'
  scope: rg
  params: {
    location: location
    searchServiceName: resolvedSearchServiceName
    searchServiceSku: searchServiceSku
    tags: { 'azd-env-name': environmentName }
  }
}

module aiHub 'modules/ai-hub.bicep' = {
  name: 'aiHub'
  scope: rg
  params: {
    location: location
    aiHubName: resolvedAiHubName
    aiServicesName: aiServices.outputs.name
    aiServicesResourceId: aiServices.outputs.resourceId
    aiServicesEndpoint: aiServices.outputs.endpoint
    storageAccountResourceId: storage.outputs.resourceId
    keyVaultResourceId: keyVault.outputs.resourceId
    searchServiceResourceId: searchService.outputs.resourceId
    searchServiceEndpoint: searchService.outputs.endpoint
    tags: { 'azd-env-name': environmentName }
  }
}

module aiProject 'modules/ai-project.bicep' = {
  name: 'aiProject'
  scope: rg
  params: {
    location: location
    aiProjectName: resolvedAiProjectName
    aiHubName: aiHub.outputs.name
    tags: { 'azd-env-name': environmentName }
  }
}

output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_AI_HUB_NAME string = aiHub.outputs.name
output AZURE_AI_PROJECT_NAME string = aiProject.outputs.name
output AZURE_AI_SERVICES_ENDPOINT string = aiServices.outputs.endpoint
output AZURE_OPENAI_ENDPOINT string = 'https://${resolvedAiServicesName}.openai.azure.com/'
output AZURE_AI_SEARCH_ENDPOINT string = searchService.outputs.endpoint
output AZURE_AI_SEARCH_INDEX_NAME string = searchIndexName
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
