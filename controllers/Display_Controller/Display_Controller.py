from controller import Supervisor
import os
import sys

# Set the project root folder
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(project_root)

# Import the ingredients dictionary
from data.ingredients import ingredients

# Initialize the Supervisor
supervisor = Supervisor()

# Time step (adjust as necessary for your simulation)
timeStep = 64

# Get the ground display device
left_display = supervisor.getDevice('left_display')
right_display = supervisor.getDevice('right_display')

# Colors
WHITE = 0xFFFFFF
BLACK = 0x000000
GREY = 0xa8a8a8
DARK_GREY = 0x2d2d2d

# Set up the display
width = left_display.getWidth()
height = left_display.getHeight()
left_display.setColor(BLACK)
left_display.fillRectangle(0, 0, width, height)
right_display.setColor(BLACK)
right_display.fillRectangle(0, 0, width, height)

# Text settings
char_height = 60
char_width = 5
dash_width = 5
left_display.setFont('Arial Black', char_height, False)
left_display.setColor(GREY)
right_display.setFont('Arial Black', char_height, False)
right_display.setColor(GREY)


# Define manual Y-axis positions (hardcoded for alignment)
y_positions = [
    95 * height / 1000,
    185 * height / 1000,
    275 * height / 1000,
    375 * height / 1000,
    460 * height / 1000,
    570 * height / 1000,
    650 * height / 1000,
    744 * height / 1000,
    825 * height / 1000,
    890 * height / 1000
]

# Draw the ingredients from the dictionary using the manually set Y-positions
for i, (key, value) in enumerate(ingredients.items()):
    ingredient_name = value["name"]
    num_dashes = 60 - len(ingredient_name)
    letter_adjustment = char_width * len(ingredient_name)
    dash_adjustment = dash_width * num_dashes
    x_pos = (25 * width / 1000) #+ letter_adjustment #- dash_adjustment  # Adjust X position based on name length
    
    if i <= 9: 
        y_pos = y_positions[i]  # Use manually defined Y position
        left_display.drawText(f"{ingredient_name} {'-' * num_dashes * 2}", x_pos, y_pos)
    else:
        y_pos = y_positions[i - 10]
        right_display.drawText(f"{'-' * num_dashes} {ingredient_name}", x_pos, y_pos)