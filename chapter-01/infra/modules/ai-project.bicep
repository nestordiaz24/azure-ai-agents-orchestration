@description('Azure region for the resource.')
param location string

@description('Name of the Azure AI Project (child workspace under the Hub).')
param aiProjectName string

@description('Name of the parent Azure AI Hub.')
param aiHubName string

@description('Resource tags.')
param tags object = {}

resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' existing = {
  name: aiHubName
}

resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: aiProjectName
  location: location
  tags: tags
  kind: 'Project'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: aiProjectName
    hubResourceId: aiHub.id
  }
}

output name string = aiProject.name
output resourceId string = aiProject.id
output principalId string = aiProject.identity.principalId
