# Home Assistant Integration Guide for pyvdcapi

This comprehensive guide demonstrates how to create a full-featured Home Assistant integration using the pyvdcapi library to expose virtual digitalSTROM devices.

## 📁 Guide Structure

This guide is organized into focused documents:

1. **[01_PROJECT_SETUP.md](01_PROJECT_SETUP.md)** - Library integration and project structure
2. **[02_CONFIG_FLOW.md](02_CONFIG_FLOW.md)** - Installation and configuration dialogue
3. **[03_SERVICE_ANNOUNCEMENT.md](03_SERVICE_ANNOUNCEMENT.md)** - Zeroconf/mDNS service discovery
4. **[04_DEVICE_CREATION_UI.md](04_DEVICE_CREATION_UI.md)** - Template-based device creation
5. **[05_MANUAL_DEVICE_CREATION.md](05_MANUAL_DEVICE_CREATION.md)** - Manual device creation flow
6. **[06_ENTITY_BINDING.md](06_ENTITY_BINDING.md)** - Binding HA entities to vDC components
7. **[COMPLETE_EXAMPLE.md](COMPLETE_EXAMPLE.md)** - Full integration code

## 🎯 What You'll Build

A Home Assistant integration that:
- ✅ Exposes HA entities as virtual digitalSTROM devices
- ✅ Announces itself via Zeroconf for automatic discovery
- ✅ Allows users to create devices from templates or manually
- ✅ Binds HA entities bidirectionally to vDC components
- ✅ Manages device lifecycle and persistence
- ✅ Provides UI-driven configuration

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Home Assistant                                                  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ pyvdcapi Integration (Custom Component)                  │  │
│  │                                                           │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐  │  │
│  │  │ Config     │  │ Device       │  │ Entity          │  │  │
│  │  │ Flow       │  │ Manager      │  │ Binding         │  │  │
│  │  │            │  │              │  │                 │  │  │
│  │  │ • Port     │  │ • Templates  │  │ • Lights → vDC │  │  │
│  │  │ • Name     │  │ • Manual     │  │ • Sensors → vDC│  │  │
│  │  │ • Settings │  │ • Validation │  │ • Switches→ vDC│  │  │
│  │  └────────────┘  └──────────────┘  └─────────────────┘  │  │
│  │                                                           │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │ pyvdcapi Library                                 │   │  │
│  │  │                                                  │   │  │
│  │  │  VdcHost → Vdc → VdSD (Virtual Devices)        │   │  │
│  │  │                                                  │   │  │
│  │  │  • Outputs (Channels)                           │   │  │
│  │  │  • Inputs (Buttons, Sensors, Binary)           │   │  │
│  │  │  • Scenes and Actions                           │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  │                           ↕                              │  │
│  │                    Zeroconf (mDNS)                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ↕
                         TCP Connection
                               ↕
┌─────────────────────────────────────────────────────────────────┐
│ digitalSTROM Server (vdSM)                                      │
│                                                                 │
│  Sees HA entities as native digitalSTROM devices               │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

### Knowledge Required
- Python async/await programming
- Home Assistant architecture basics
- Home Assistant integration development
- YAML configuration
- Basic networking (TCP, mDNS/Zeroconf)

### Tools & Environment
- Home Assistant development environment
- Python 3.11 or newer
- VS Code with Home Assistant extension (recommended)
- Access to a digitalSTROM Server (vdSM) for testing

## 🚀 Quick Start

### For End Users (Installing the Integration)
1. **Install the integration**: [00_INSTALLATION.md](00_INSTALLATION.md)
2. **Configure and create devices**: [04_DEVICE_CREATION_UI.md](04_DEVICE_CREATION_UI.md)

### For Developers (Building the Integration)
1. **Read the setup guide**: [01_PROJECT_SETUP.md](01_PROJECT_SETUP.md)
2. **Set up config flow**: [02_CONFIG_FLOW.md](02_CONFIG_FLOW.md)
3. **Add service announcement**: [03_SERVICE_ANNOUNCEMENT.md](03_SERVICE_ANNOUNCEMENT.md)
4. **Implement template device creation**: [04_DEVICE_CREATION_UI.md](04_DEVICE_CREATION_UI.md)
5. **Implement manual device creation**: [05_MANUAL_DEVICE_CREATION.md](05_MANUAL_DEVICE_CREATION.md)
6. **Bind entities**: [06_ENTITY_BINDING.md](06_ENTITY_BINDING.md)
7. **Review complete example**: [COMPLETE_EXAMPLE.md](COMPLETE_EXAMPLE.md)

## 🎓 Learning Path

### Beginner
Start with the basics:
1. Installing the integration ([00_INSTALLATION.md](00_INSTALLATION.md))
2. Project setup and library integration ([01_PROJECT_SETUP.md](01_PROJECT_SETUP.md))
3. Basic config flow ([02_CONFIG_FLOW.md](02_CONFIG_FLOW.md))
4. Simple device creation (one entity → one device)

### Intermediate
Add advanced features:
1. Template-based device creation ([04_DEVICE_CREATION_UI.md](04_DEVICE_CREATION_UI.md))
2. Manual device configuration ([05_MANUAL_DEVICE_CREATION.md](05_MANUAL_DEVICE_CREATION.md))
3. Multi-channel devices (RGB lights)
4. Sensor and button inputs

### Advanced
Full integration:
1. Entity binding system ([06_ENTITY_BINDING.md](06_ENTITY_BINDING.md))
2. Dynamic device discovery
3. Scene management
4. Custom actions and states
5. Complete production-ready integration ([COMPLETE_EXAMPLE.md](COMPLETE_EXAMPLE.md))
6. Error handling and validation

## 📚 Additional Resources

### pyvdcapi Documentation
- [Main README](../../README.md)
- [Template System](../../pyvdcapi/templates/README.md)
- [API Reference](../../API_REFERENCE.md)
- [Property Reference](../../PROPERTY_REFERENCE.md)

### Home Assistant Documentation
- [Integration Development](https://developers.home-assistant.io/docs/creating_integration_manifest)
- [Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)
- [Entity](https://developers.home-assistant.io/docs/core/entity)

### digitalSTROM API
- [vDC API Documentation](../../Documentation/vdc-API/)
- [Service Announcement](../../SERVICE_ANNOUNCEMENT.md)

## 🤝 Contributing

Found an issue or have an improvement? Please contribute:
1. Test the integration thoroughly
2. Document any issues or unclear sections
3. Submit improvements via pull request

## ⚠️ Important Notes

### Library Installation
**pyvdcapi is not yet available on PyPI**. This guide covers:
- Direct git submodule integration
- Local path dependencies
- Development workflow

### Async Requirements
pyvdcapi uses async/await extensively. Your HA integration **must**:
- Run all pyvdcapi operations in async context
- Use `hass.async_add_executor_job()` for any blocking operations
- Properly handle async cleanup on shutdown

### Network Considerations
- vDC host requires a unique TCP port
- Zeroconf service must be properly announced
- Ensure firewall allows incoming connections

Let's get started! 🚀
