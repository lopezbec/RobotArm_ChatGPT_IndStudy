# Source ingredients dictionary containing the names of and positions of the 20 standardized ingredients
# Accessed by both the display controller to display the names in the environment and by the system prompt

ingredients = {
    "I1": {"name": 'eggs', "direction": 1.00}, 
    "I2": {"name": 'milk', "direction": 1.15}, 
    "I3": {"name": 'cheddar cheese', "direction": 1.30}, 
    "I4": {"name": 'parmesan cheese', "direction": 1.45}, 
    "I5": {"name": 'onions', "direction": 1.60}, 
    "I6": {"name": 'green bell peppers', "direction": 1.75}, 
    "I7": {"name": 'red bell peppers', "direction": 1.90}, 
    "I8": {"name": 'mushrooms', "direction": 2.05},
    "I9": {"name": 'spinach', "direction": 2.20}, 
    "I10": {"name": 'tomatoes', "direction": 2.35}, 
    "I11": {"name": 'bacon bits', "direction": -2.35}, 
    "I12": {"name": 'sausage', "direction": -2.20}, 
    "I13": {"name": 'ham', "direction": -2.05}, 
    "I14": {"name": 'salt', "direction": -1.90}, 
    "I15": {"name": 'black pepper', "direction": -1.75}, 
    "I16": {"name": 'butter', "direction": -1.60},
    "I17": {"name": 'olive oil', "direction": -1.45},
    "I18": {"name": 'garlic', "direction": -1.30},
    "I19": {"name": 'hot sauce', "direction": -1.15},
    "I20": {"name": 'herbs', "direction": -1.00}
    }