@description('Azure region for the resource.')
param location string

@description('Name of the Azure AI Search service.')
param searchServiceName string

@description('SKU for the search service.')
@allowed(['free', 'basic', 'standard', 'standard2', 'standard3'])
param searchServiceSku string = 'basic'

@description('Resource tags.')
param tags object = {}

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: {
    name: searchServiceSku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    semanticSearch: 'free'
  }
}

output name string = searchService.name
output resourceId string = searchService.id
output endpoint string = 'https://${searchService.name}.search.windows.net'
