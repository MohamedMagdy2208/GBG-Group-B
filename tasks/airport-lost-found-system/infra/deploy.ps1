param(
  [Parameter(Mandatory = $true)]
  [string]$ResourceGroup,

  [Parameter(Mandatory = $true)]
  [string]$Location,

  [Parameter(Mandatory = $true)]
  [string]$ParametersFile
)

az group create --name $ResourceGroup --location $Location
az deployment group create `
  --resource-group $ResourceGroup `
  --template-file "$PSScriptRoot/main.bicep" `
  --parameters "@$ParametersFile"
