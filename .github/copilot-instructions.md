# SmartIR Copilot Instructions

## Project Overview
SmartIR is a Home Assistant custom integration for controlling climate, fan, media player, and light devices via infrared (IR) controllers. It supports multiple controller types (Broadlink, Xiaomi, LOOK.in, ESPHome, MQTT, ZHA, Tuya Z06/Moes UFO-R11) and uses device-specific JSON code files for IR commands.

## Architecture & Key Components
- **custom_components/smartir/**: Main integration code. Entry points for each platform: `climate.py`, `fan.py`, `media_player.py`, `light.py`.
- **controller.py**: Abstracts controller-specific logic. Use `get_controller()` to instantiate the correct controller class based on config.
- **smartir_entity.py**: Shared base logic for SmartIR entities. Handles config schema, device data loading, and controller integration.
- **codes/** & **custom_codes/**: Device IR code files (JSON). `codes/` is managed by HACS and overwritten on update; `custom_codes/` is user-persistent.
- **docs/**: Platform-specific documentation and code syntax guides.

## Developer Workflows
- **Configuration**: All platforms use `PLATFORM_SCHEMA` (voluptuous) for config validation. See each platform file for required/optional fields.
- **Device Data Loading**: Use `load_device_data_file()` from `smartir_entity.py` to load device JSON files. Custom files go in `custom_codes/`.
- **Debug Logging**: Enable debug logs for troubleshooting:
  ```yaml
  custom_components.smartir.climate: debug
  custom_components.smartir.fan: debug
  custom_components.smartir.media_player: debug
  custom_components.smartir.light: debug
  ```
- **Testing**: No automated tests found; manual validation via Home Assistant recommended.

## Patterns & Conventions
- **Async/Await**: All entity setup and command methods are async for Home Assistant compatibility.
- **Config Validation**: Use `voluptuous` and `cv` for all config schemas.
- **Entity Features**: Supported features are set via `_attr_supported_features` class attribute (see Home Assistant docs for details).
- **Device Data Files**: Always use the correct directory (`codes/` for built-in, `custom_codes/` for user files). File naming: `<device_code>.json`.
- **Controller Selection**: Use `get_controller()` to abstract controller differences; do not hardcode controller logic in platform files.

## Integration Points
- **Home Assistant**: All entities inherit from Home Assistant base classes (`ClimateEntity`, `FanEntity`, etc.).
- **External Controllers**: Integration via controller classes in `controller.py`.
- **IR Code Conversion**: For migrating codes, see README and docs for conversion scripts and guides.

## Examples
- See `custom_components/smartir/climate.py` for a typical entity implementation and config schema.
- See `docs/CLIMATE_CODES.md` for device code file format.
- See `controller.py` for controller abstraction pattern.

---
If any section is unclear or missing, please specify what needs improvement or what additional context is required.
