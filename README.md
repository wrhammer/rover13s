# Rover13s LinuxCNC Configuration

This repository contains the LinuxCNC configuration for the Rover13s CNC machine, a custom router/saw combination machine with multiple vertical and horizontal spindles.

## Machine Overview

- **Controller**: Mesa 7i96s with additional 7i77 and 7i84 cards
- **Axes**: 3-axis (XYZ) configuration 
            Reconfigured X to be parallel with gantry, Y to be perpendicular. Original Biesse config was opposite.
- **Tools**: 20 tool positions
  - T1-T5: Individual Vertical Y-axis bits
  - T6-T10: Individual Vertical X-axis bits
  - T11-T16: Horizontal shared bits
  - T17: Saw blade
  - T18: Combined Vertical Y spindles (T1-T5)
  - T19: Combined Vertical X spindles (T6-T10)
  - T20: Main router

## Installation

1. Clone this repository to your LinuxCNC configs directory:
```bash
cd /home/cnc/linuxcnc/configs
git clone https://github.com/wrhammer/rover13s.git
```

2. Make Python scripts executable:
```bash
cd /home/cnc/linuxcnc/configs/rover13s
chmod +x python/*.py
```

## Configuration Files

### Core Configuration
- `Rover13s.ini` - Main configuration file
- `tool.tbl` - Tool table with all tool definitions
- `rover-custom.hal` - Custom HAL file for machine-specific connections
- `custom_postgui.hal` - Post-GUI HAL configurations

### Python Components
- `python/work_area_control.py` - Work area and vacuum control
- `python/tool_release_control.py` - Tool change management
- `python/vfd_control.py` - VFD (spindle) control
- `python/remap.py` - M-code remapping for tool changes and special functions

## Tool Configuration

## M-Code Pin Assignments (set in rover-custom.hal)
- **P0-P4**: Vertical Y bits (T1-T5)
- **P5-P9**: Vertical X bits (T6-T10)
- **P10-P12**: Horizontal shared bits (T11-T16)
- **P13-P14**: Router control (T20)
- **P15-P16**: Saw blade control (T17)

### Special Features
- **Combined Tools**: T18 and T19 activate multiple bits simultaneously
- **Shared Pins**: Horizontal bits share control pins (T11/12, T13/14, T15/16)
- **Manual Tool Change**: Required only for T20 (router)

## Custom M-Codes

- **M6**: Remapped for custom tool change behavior
  - Automatic tool changes for T1-T19 that are the integrated vertical and horizontal bit and the saw blade
  - Manual tool change prompt for router bits, T20 and above
  - Integrated safety checks and position verification

- **M8/M9**: Repurposed coolant control for bit retraction
  - M8: Retracts all bits (T1-T19)
  - M9: No operation (placeholder)

## Safety Features

1. **Emergency Stop**
   - Hardware E-stop integration
   - Software safety interlocks

2. **Work Area Control**
   - Photo-eye protection
   - Left/Right work area setup
   - Vacuum control integration

3. **Tool Change Safety**
   - Position verification
   - Tool presence detection
   - Automatic bit retraction

## Maintenance

### Regular Checks
1. Verify all tool positions in `tool.tbl`
2. Check vacuum system operation
3. Verify photo-eye functionality
4. Test emergency stop system

### Troubleshooting
1. Check HAL pins status:
```bash
halcmd show pin
```

2. Monitor Python component status:
```bash
halcmd show comp
```

3. View error messages:
```bash
tail -f /var/log/linuxcnc.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

This project is licensed under the GPL License - see the LICENSE file for details.

## Acknowledgments

- LinuxCNC community
- Mesa Electronics for hardware support
- Contributors and testers

## Contact

For support or questions, please open an issue in the GitHub repository.
