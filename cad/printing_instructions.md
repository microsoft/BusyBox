# Printing Guide

For our prints we used the Bambu P1S with the Bambu Studio.

We used standard Bambu filament with the default printing presets and using Tree supports.

Some of our prints utilize the "Multi-Color Printing" feature on the Bambu P1S.

## Recipe for printing canonical BusyBox configuration

All prints exist at `BusyBox/cad/BusyBoxCad`.


Each of the following are printed individually with different filaments colors:

| Part Type        | BusyBox Part                 | Number of Items | Multi-color |
|------------------|------------------------------|-----------------|-------------|
| Box_Frame        | Box_Bottom.stl               | 6               | no          |
| -                | Single_side.stl              | 6               | no          |
| -                | Handle.stl                   | 2               | no          |
| Button_Module    | Button_Box.stl               | 1               | no          |
| Display_Module   | Display_Box.stl              | 1               | no          |
| -                | Display_Holder.stl           | 1               | no          |
| Knob_Module      | Rotary_Box.stl               | 1               | no          |
| -                | Rotary_Knob.stl              | 1               | no          |
| -                | Rotary_Text_Multicolor.3mf   | 1               | yes         |
| Slider_Module    | Slider_Box.stl               | 1               | no          |
| -                | Slider_Knobs_Multicolor.3mf  | 2               | yes         |
| -                | Slider_Text.3mf              | 1               | yes         |
| Switch_Module    | Switch_Box.stl               | 1               | no          |
| -                | Switch_Text_Multicolor.3mf   | 1               | yes         |
| Wire_Module      | Wire_Module.stl              | 1               | no          |


## Tips

 - print the "box" parts with the faceplate on the printing bed. 