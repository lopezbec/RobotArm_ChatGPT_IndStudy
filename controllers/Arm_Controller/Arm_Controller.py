from openai import OpenAI
import re
from controller import Robot
import os
import sys

# Set the project root folder
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(project_root)

# Import the ingredients dictionary
from data.ingredients import ingredients

client = OpenAI(api_key = "OPENAI_API_KEY")

order = "Hi there, I would like an creamy omlette with onions, spinach and cheddar cheese please"

user_prompt = f"""
Customer's order : {order} 
Ingredient_List: {ingredients}
Robot_Behaviors [execution time]: 

add_ingredient(“a”) [13 secs] a = ingredient name from ingredient_list
heat_on(“b”) [10 secs] b = heating level [low, medium, or high] 
wait(c) [c secs] c = wait time [seconds] 
grab_spatula() [11 seconds]
stir_spatula(d) [d secs] d = stirring stime [seconds]
return_spatula() [12 secs]
heat_off() [10 secs]
serve() [8 secs]

Execute each step of the system prompt using the included information.
"""
        
system_prompt = """
You are a specialized kitchen robot controller whose task is to orchestrate a series of robot behaviors in order to cook a customer's dish.
The list of robot behaviors and ingredients available will be provided in the user prompt.

Complete each step, one by one, and number each step of your response:
1) What dish did the customer order? What specifics were provided about its preperation?
2) What temperature should the stove be at to cook the order? [low, medium, high]
3) What is the typically cook time for the dish? Modulate this cook time if the customer specifically requested the dish be cooked a certain amount.
4) What ingredients from ingredients_list are needed to prepare the dish?
5) What sequence of behaviors from robot_behaviors are needed to prepare the dish? 
6) Provide a list, in brackets, separated by commas, which contains the refined behavior sequence.
Valid list example: [add_ingredient("I13"), add_ingredient("I4"), add_ingredient("I20"), heat_on("high"), grab_spatula(), stir_spatula(20), return_spatula(), heat_off("high"), grab_pan_to_serve(), serve()]
7) SUM the behavior execution times between heat_on and heat_off. 
8) Does this SUM equal the required cook time? If not, complete 8a), 8b), 8c) to generate a new list. Else continue to step 9)
    8a) Calculate: difference = required cook time - SUM 
    8b) Add this difference across the input times of behaviors between heat_on and heat_off. Generate a new list with the new times.
    8c) Repeat step 7 and 8 until the SUM equals the required cook time
9) Output the final valid list with the following format, and do not include explanations, reasoning, or additional text:
AAA[List]BBB
"""
# Ingredients and Cook time steps completed before list because they are inputs to behaviors 

# Initialize the robot and timestep
robot = Robot()
time_step = int(robot.getBasicTimeStep()) # float utilized by webots to iterate the simulation through time [miliseconds]

# Initialize global variables
simtime = 0                # float to hold the simulation time in seconds
main_step = 0              # int to be iterated after the completion of a part program (i.e API Call, Arm setup, and Behavior sequence execution)
behavior_step = 0          # int to be iterated after the completion of a behavior
behavior_step_change = -1  # int to enable check for change in behavior_step
serve_step = 0             # int to be iterated after each subsequence of serve()
ingredient_step = 0        # int to be iterated after each subsequence of add_ingredient() 
heat_on_step = 0           # int to be iterated after each subsequence of heat_on()
heat_off_step = 0          # int to be iterated after each subsequence of heat_off()
nob_turn = 0               # float to hold amount stove nob was turned
wait_step = 0              # int to be iterated after each subsequence of wait()
wait_start_time = 0        # int to track the start time of the wait
grab_step = 0              # int to be iterated after each subsequence of grab_spatula()
return_spatula_step = 0    # int to be iterated after each subsequence of return_spatula()
stir_step = 0              # int to be iterated after each subsequence of stir_spatula()
stir_start_time = 0        # int to track the start time of the stir behavior
flop = 1                   # int to switch between cw or ccw stir direction 
print_once = 0             # int to ensure final print function only runs once 
api_response = ""          # str to hold api response globally


####################
### Dictionaries ###
####################
# Dictionary to simplfiy the standard motor call names
motor_names = {"M1": "motor 1", "M2": "motor 2", "M3": "motor 3", "M4": "motor 4", "M5": "motor 5", "M6": "motor 6", "M7": "gripper::right"}
motors = {}  # Dictionary to store initialized motors
position_sensors = {}  # Dictionary to store position sensors
motor_targets = {key: None for key in motor_names.keys()}  # Dictionary to store target positions for motors

###################################################
### Initialize motors & basic control functions ###
###################################################
for abbreviation, motor_name in motor_names.items():
    motor = robot.getDevice(motor_name)             # Get the motor device object
    if motor:
        motor.setPosition(float('inf'))             # Set to velocity control mode
        motor.setVelocity(0)                        # Set velocity to 0
        motors[abbreviation] = motor                # Store the motor in dictionary with its abbreviation
        sensor = motor.getPositionSensor()          # Var for the current motor position
        if sensor:
            sensor.enable(time_step)                # Enable the sensor with the simulation time step
            position_sensors[abbreviation] = sensor # Store the sensor object in dictionary for easier reference
        else:
            print(f"Error: Position sensor for {motor_name} not found!")
    else:
        print(f"Error: {motor_name} not found!")

def set_motor(abbreviation, position, velocity=1.2):
    """
    Sets the motor's velocity, position, and a target value which will be used to determine
    if the set_motor() command has fully executed successfully
    """
    if abbreviation in motors:
        if abbreviation == "M7" and velocity == 1.2: velocity = 1   # Adjust default velocity for M7 because its max possible velocity < 1.2
        motors[abbreviation].setVelocity(velocity)                  # Set motor velocity
        motors[abbreviation].setPosition(position)                  # Set motor position
        motor_targets[abbreviation] = position                      # Update target position for the motor
    else:
        print(f"Error: Motor {abbreviation} not initialized.")

def all_motors_reached():
    """
    Checks if all motors with non-None targets have reached their positions.
    Increments `behavior_step` if all targets are reached.
    """
    for abbreviation, target in motor_targets.items():
        if target is None: # Skip motors with no target set
            continue
        # If any motor has not reached its target, return false
        if not abs(position_sensors[abbreviation].getValue() - motor_targets[abbreviation]) <= 0.01:
            return False
    # If all targets are reached, reset targets and return true
    for abbreviation in motor_targets:
        motor_targets[abbreviation] = None  # Reset target
    return True

########################
### Robot Behaviors ####
########################
def setup():
    global main_step
    set_motor("M1", 0); set_motor("M2", -1.6); set_motor("M3", -1.6) 
    set_motor("M5", 1.8); set_motor("M6", 0); set_motor("M7", 0.25)
    if all_motors_reached(): main_step += 1

def add_ingredient(ingredient_number):
    global ingredient_step, behavior_step
    
    if ingredient_step == 0:                            # Face arm towards ingredient position
        set_motor("M1", ingredients[ingredient_number]["direction"])
        if all_motors_reached(): ingredient_step += 1
    elif ingredient_step == 1:                          # Extend arm towards ingredient
        set_motor("M2", -1.3); set_motor("M5", 1.0)
        if all_motors_reached(): ingredient_step += 1
    elif ingredient_step == 2:                          # Close claw to grab ingredient item
        set_motor("M7", 0.10)
        if all_motors_reached(): ingredient_step += 1
    elif ingredient_step == 3:                          # Lift item above plane of other ingredients
        set_motor("M2", -.75); set_motor("M5", 0.8)
        if all_motors_reached(): ingredient_step += 1
    elif ingredient_step == 4:                          # Return to face stove
        set_motor("M1", 0.1)
        if all_motors_reached(): ingredient_step += 1
    elif ingredient_step == 5:                          # Adjust item to be above pan
        set_motor("M2", -1.3); set_motor("M5", 1.0); set_motor("M3", -1.3)
        if all_motors_reached(): ingredient_step += 1
    elif ingredient_step == 6:                          # Open Claw to drop ingredient in pan
        set_motor("M7", .25)
        if all_motors_reached(): ingredient_step += 1
    elif ingredient_step == 7:                          # Center arm away from pan
        set_motor("M1", 0)
        if all_motors_reached(): ingredient_step += 1
    elif ingredient_step == 8:                          # Retract arm 
        set_motor("M3", -1.6); set_motor("M5", 1.8)
        if all_motors_reached(): ingredient_step += 1            
    elif ingredient_step == 9:                          # Complete arm reset
        set_motor("M2", -1.6); set_motor("M6", 0); set_motor("M7", 0.25)
        if all_motors_reached(): behavior_step += 1; ingredient_step = 0 

def serve():
    global behavior_step, serve_step
    if serve_step == 0:
        set_motor("M1", 0.1); set_motor("M2", -1.0); set_motor("M5", .5); set_motor("M7", 0, .06)
        if all_motors_reached(): serve_step +=1
    elif serve_step == 1:
        set_motor("M1", -.25)
        set_motor("M2", -1)
        set_motor("M3", -1.1)
        set_motor("M5", 0)
        if all_motors_reached(): serve_step +=1
    elif serve_step == 2:     
        set_motor("M6", 2)
        if all_motors_reached(): behavior_step +=1; serve_step = 0

def heat_on(heat_level):
    global behavior_step, heat_on_step
    
    if heat_level == "low": nob_turn = .5
    elif heat_level == "medium": nob_turn = 1.5
    elif heat_level == "high": nob_turn = 2.5
    else: print("invalid heating level")
    
    if heat_on_step == 0:
        set_motor("M1", -0.7)
        set_motor("M4", -0.7)
        if all_motors_reached(): heat_on_step += 1
    elif heat_on_step == 1:
        set_motor("M1", -0.6)
        set_motor("M2", -1.9)
        set_motor("M3", -1.2)
        set_motor("M4", -0.6)
        set_motor("M5", 1.55)
        set_motor("M7", 0.05)
        if all_motors_reached(): heat_on_step += 1
    elif heat_on_step == 2:
        set_motor("M6", nob_turn)
        if all_motors_reached(): heat_on_step += 1
    elif heat_on_step == 3:
        set_motor("M1", -.9)
        set_motor("M4", -.9)
        set_motor("M5", 1.8)
        set_motor("M6", 0)
        set_motor("M7", 0.25)
        if all_motors_reached(): heat_on_step += 1
    elif heat_on_step == 4:
        set_motor("M1", 0)
        set_motor("M4", 0)
        set_motor("M2", -1.6)
        set_motor("M3", -1.6)
        if all_motors_reached(): behavior_step += 1; heat_on_step = 0

def heat_off():
    global behavior_step, heat_off_step, nob_turn
    
    if heat_off_step == 0:
        set_motor("M1", -0.7)
        set_motor("M4", -0.7)
        set_motor("M6", nob_turn)
        if all_motors_reached(): heat_off_step += 1
    elif heat_off_step == 1:
        set_motor("M1", -0.6)
        set_motor("M2", -1.9)
        set_motor("M3", -1.2)
        set_motor("M4", -0.6)
        set_motor("M5", 1.55)
        set_motor("M7", 0.05)
        if all_motors_reached(): heat_off_step += 1
    elif heat_off_step == 2:
        set_motor("M6", 0)
        if all_motors_reached(): heat_off_step += 1
    elif heat_off_step == 3:
        set_motor("M1", -.9)
        set_motor("M4", -.9)
        set_motor("M5", 1.8)
        set_motor("M7", 0.25)
        if all_motors_reached(): heat_off_step += 1
    elif heat_off_step == 4:
        set_motor("M1", 0)
        set_motor("M4", 0)
        set_motor("M2", -1.6)
        set_motor("M3", -1.6)
        if all_motors_reached(): behavior_step += 1; heat_off_step = 0
             
def wait(duration):
    global wait_step, wait_start_time, simtime, behavior_step
    if wait_step == 0:  wait_start_time = simtime; wait_step += 1
    elif wait_step == 1:  
        print(f"Waiting... {simtime - wait_start_time:.2f} of {duration}")
        if simtime - wait_start_time >= duration:   # Check if the wait duration has elapsed
            wait_step = 0                           # Reset the wait state
            behavior_step += 1                      # Iterate to next behavior

def grab_spatula():
    global grab_step, behavior_step
    
    if grab_step == 0:
        set_motor("M1", 0.43)
        set_motor("M2", -1.2)
        set_motor("M3", 0)
        set_motor("M5", -1.80)
        set_motor("M6", -1.1)
        if all_motors_reached(): grab_step += 1
    elif grab_step == 1:
        set_motor("M5", -1.6)
        set_motor("M2", -1.55)
        if all_motors_reached(): grab_step += 1
    elif grab_step == 2:
        set_motor("M7", 0)
        if all_motors_reached(): grab_step += 1
    elif grab_step == 3:
        set_motor("M2", -1.2) 
        set_motor("M5", -1.90)  
        if all_motors_reached(): grab_step += 1      
    elif grab_step == 4:
        set_motor("M2", -0.6) 
        set_motor("M1", 0.1)
        if all_motors_reached(): grab_step += 1
    elif grab_step == 5:
        set_motor("M2", -1.225)
        set_motor("M5", -1.35)
        if all_motors_reached(): grab_step = 0; behavior_step += 1

def return_spatula():
    global return_spatula_step, behavior_step
    if return_spatula_step == 0:
        set_motor("M2", -0.6)
        set_motor("M5", -1.90)  
        if all_motors_reached(): return_spatula_step += 1 
    if return_spatula_step == 1:    
        set_motor("M1", 0.40)
        set_motor("M2", -1.2)
        set_motor("M3", 0)
        set_motor("M5", -1.9, 2)
        set_motor("M6", -1.1)
        if all_motors_reached(): return_spatula_step += 1
    if return_spatula_step == 2:
        set_motor("M5", -1.73)
        set_motor("M2", -1.4, 0.25)
        if all_motors_reached(): return_spatula_step += 1
    if return_spatula_step == 3:
        set_motor("M2", -1.5, 0.25)
        set_motor("M5", -1.6)
        set_motor("M7", .25)
        if all_motors_reached(): return_spatula_step += 1
    if return_spatula_step == 4:
        set_motor("M1", 0)
        set_motor("M2", -1.0)
        set_motor("M5", -1.9)
        if all_motors_reached(): return_spatula_step += 1
    if return_spatula_step == 5:
        set_motor("M5", 1.6, 2)
        set_motor("M3", -.8)
        if all_motors_reached(): return_spatula_step += 1
    if return_spatula_step == 6: 
        set_motor("M1", 0)
        set_motor("M2", -1.6)
        set_motor("M3", -1.6)
        set_motor("M5", 1.8)
        set_motor("M6", 0)
        set_motor("M7", 0.25); 
        if all_motors_reached(): return_spatula_step = 0; behavior_step += 1 

def stir_spatula(duration):
    global stir_step, stir_start_time, simtime, behavior_step, flop
    if stir_step == 0:  
        stir_start_time = simtime # Set time with which stir is starting
        stir_step += 1
    elif stir_step == 1:    
        set_motor("M6", 2.95*flop, 2.79)
        print(f"Stirring... {simtime - stir_start_time:.2f} of {duration}")
        if all_motors_reached(): flop *= -1
        if simtime - stir_start_time >= duration: stir_step += 1
    elif stir_step == 2: 
        set_motor("M6", 0, 2.79)  
        if all_motors_reached(): stir_step += 1
    elif stir_step == 3: 
        behavior_step += 1  # Iteriate to next behavior
        stir_step = 0       # Reset the stir step
        

#########################
### Main control loop ###
#########################
while robot.step(time_step) != -1:
    simtime += time_step / 1000.0  # Update simulation time
    if main_step == 0:  
        completion = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}])
        api_response = completion.choices[0].message.content
        print(f"SYSTEM PROMPT:\n{system_prompt}\n ")
        print(f"USER PROMPT:\n{user_prompt}\n ")
        print(f"FULL GPT RESPONSE:\n{api_response}\n ")
        # Use regex to extract gpt-produced behavior list within AAA and BBB delimeters
        match = re.search(r"AAA(.*?)BBB", api_response, re.DOTALL)
        if match:
            extracted_list_string = match.group(1).strip()
        else:
            print("Delimiters not found.")
        main_step += 1
    elif main_step == 1: setup()
    elif main_step == 2:
        #print(behavior_step)
        function_calls = extracted_list_string.strip("[]").split(", ") # Remove the square brackets and split the function calls
        if print_once == 0: print(f"EXTRACTED GPT-GENERATED MOTOR COMMAND SEQUENCE: {function_calls}"); print_once +=1
        for func in function_calls:
            if function_calls.index(func) == behavior_step:
                if behavior_step_change != behavior_step: print(f"Executing: {func}")
                behavior_step_change = behavior_step
                eval(func)  # Execute the function
                
