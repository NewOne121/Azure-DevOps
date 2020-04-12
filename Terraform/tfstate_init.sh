#!/bin/bash

az group create --location eastus --name default

az storage account create --name defaulttfstate --resource-group default --access-tier cool --kind blobstorage --location eastus

az storage container create --name ffptfstatepractice --account-name defaulttfstate --auth-mode key --account-key\
 $(az storage account keys list --account-name defaulttfstate\
 | grep -A3 key1\
 | awk '/value/ {gsub ("\"",""); print $2}')

az ad sp create-for-rbac --name terrafromservice