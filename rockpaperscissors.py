import random

r = 'Rock'
p = 'Paper'
s = 'Scissors'

rul = [r, p, s]

game = """The game "Rock, Paper, Scissors" (Carta, Forbici, Sasso) is a simple hand game usually played between two people. Here are the basic rules:

Rock (Sasso) beats Scissors (Forbici) – Rock crushes Scissors.

Scissors (Forbici) beats Paper (Carta) – Scissors cuts Paper.

Paper (Carta) beats Rock (Sasso) – Paper covers Rock."""

def games():
    print(game)
    action = input("Your choose: 'Rock' (r), 'Paper' (p), 'Scissors' (s): ")
    
    if action == 'r' or action == 'R':
        bot_choice = random.choice(rul)
        print(f"The bot chose {bot_choice}")
        if bot_choice == p: 
            print("You loose") 
        elif bot_choice == s: 
            print("You won") 
        elif bot_choice == r:
            print("It's a tie!")
            
    elif action == 'p' or action == 'P': 
        bot_choice = random.choice(rul)
        print(f"The bot chose {bot_choice}")
        if bot_choice == r: 
            print("You won") 
        elif bot_choice == s:
            print("You loose") 
        elif bot_choice == p:
            print("It's a tie!")
            
    elif action == 's' or action == 'S': 
        bot_choice = random.choice(rul)
        print(f"The bot chose {bot_choice}")
        if bot_choice == r: 
            print("You loose") 
        elif bot_choice == p: 
            print("You won")
        elif bot_choice == s:
            print("It's a tie!")

while True: 
    ans = input("Are you ready to play? (S/N): ")
    if ans == 'S' or ans == 's': 
        games() 
    else: 
        print("Okay, goodbye!")
        break
