@description('Azure region for the resource.')
param location string

@description('Name of the Azure AI Services (OpenAI) account.')
param aiServicesName string

@description('Model to deploy.')
param modelName string

@description('Model version.')
param modelVersion string

@description('Provisioned throughput capacity (TPM in thousands).')
param modelCapacity int

@description('Resource tags.')
param tags object = {}

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: aiServicesName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aiServicesName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: aiServices
  name: modelName
  sku: {
    name: 'GlobalStandard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
  }
}

output name string = aiServices.name
output resourceId string = aiServices.id
output endpoint string = aiServices.properties.endpoint
output modelDeploymentName string = modelDeployment.name
