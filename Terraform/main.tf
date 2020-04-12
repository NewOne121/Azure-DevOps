provider "azurerm" {
  version = ">= 2.0"
  features {}
}

resource "azurerm_resource_group" "name" {
  name     = ""
  location = ""

  tags = {
    environment = "practice"
  }
}

resource "azurerm_virtual_network" "az-dev" {
  name                = "az-network"
  address_space       = ["10.1.0.0/16"]
  location            = azurerm_resource_group.tf-practice.location
  resource_group_name = azurerm_resource_group.tf-practice.name
}

resource "azurerm_subnet" "az-int" {
  name                 = "az-int"
  resource_group_name  = azurerm_resource_group.tf-practice.name
  virtual_network_name = azurerm_virtual_network.az-dev.name
  address_prefix       = "10.1.1.0/24"
}

resource "azurerm_network_interface" "az-netint" {
  name                = "worker-netint"
  location            = azurerm_resource_group.tf-practice.location
  resource_group_name = azurerm_resource_group.tf-practice.name

  ip_configuration {
    name                          = "testconfiguration1"
    subnet_id                     = azurerm_subnet.az-int.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_public_ip" "bastion-ip" {
  name                = "Bastion_public"
  location            = azurerm_resource_group.tf-practice.location
  resource_group_name = azurerm_resource_group.tf-practice.name
  allocation_method   = "Dynamic"

  tags = {
    purpose = "Gateway"
  }
}

resource "azurerm_virtual_machine" "az-bastion" {
  name                  = "bastion-vm"
  location              = azurerm_resource_group.tf-practice.location
  resource_group_name   = azurerm_resource_group.tf-practice.name
  network_interface_ids = [azurerm_network_interface.az-netint.id]
  vm_size               = "Standard_A1_v2"
  # delete_os_disk_on_termination = true

  storage_image_reference {
    offer = "CentOS"
    publisher = "OpenLogic"
    sku = "7.5"
    version   = "latest"
  }
  storage_os_disk {
    name              = "myosdisk1"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }
  os_profile {
    computer_name  = "az-bastion"
    admin_username = "opsteam"
    admin_password = "Password12345"
  }
  os_profile_linux_config {
    disable_password_authentication = false
  }
  tags = {
    environment = "practice"
  }
}
