```bash
systemctl status game-bringup.service
```

```bash
#!/bin/bash
# Activate conda environment and run game
source /home/morrissharp/miniconda3/etc/profile.d/conda.sh
conda activate device_search
python /home/morrissharp/Documents/macgyver-demo/game/game_bringup.py
```
