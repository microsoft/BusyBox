# BusyBox: Benchmarking Affordance Generalization

BusyBox is a physical 3D-printable device for benchmarking affordance generalization in robot foundation models.

![busybox_assembled](assets/shuffled_box_config_1_background_removed.png)

It features

 - Modular design with 6 interchangeable modules (buttons, switches, sliders, wires, knob, and display)  
 - Open-source CAD files and bill of materials for easy reproduction  
 - Optional electronics and Raspberry Pi instrumentation for automated state logging  
 - Reconfigurable setups enabling systematic evaluation of generalization  
 - A language-annotated dataset of 1000+ demonstration trajectories oof BusyBox affordances  

Please check out our [website]() for more details.


## Quick-Start

```bash
systemctl status evaluate-bringup.service
systemctl enable evaluate-bringup.service
systemctl restart evaluate-bringup.service
```
The `evaluate_bringup` will now be running and the BusyBox is recording its states during rollouts.

## BusyBox assembly instructions

For fully building a instrumented BusyBox capable of state logging, see the [BOM](). TODO: add BOM.

First print the BusyBox following [Printing Instructions](cad/printing_instructions.md) with details on files to print and any details on print settings.

## Electronic Assembly:

TODO: add instructions on how to assemble electronics with pictures

## Firmware Flashing:

TODO: add instructions on how to flash Arduino Nanos with firmware. 

## Data Collection Guide

See [Data Collection](assets/taskbox_data_collection.docx) for a look into how we collected our data.
