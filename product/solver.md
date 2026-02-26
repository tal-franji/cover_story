# Cover-Story game solver
We want to create a web app that allows user to share/uload a screenshot of the game, and get the solution.

## Game rules
There is a 5*5 board with 25 cells, each cell can be colored in one of 4 colors.
There are several pices (tetris like shapes) composed of 2 to 4 squares each.
The sum of their sizes is 25. e.g. 5 pices of size 4, 1 os size 3 and 1 of size 2. The pices are given in a specific orientation and cannot be rotated.
You need to cover the board with the pieces, without overlapping, and without leaving any cell uncovered.
Also each piece cannot cover the same collor twice. That is, if we have a piece of size 4 it needs to cover 4 different colors.

## Game input
The game is uploaded as a screenshot of the game, with the board and the pieces.
See file `cover_story_screen.jpeg` for an example.
The user should be shown an image of the identified grid and pices highlighted in a way that allows him/her to check that the image processing went well.
(we may elimintate this step if we find image processing is mostly fine)

## Game output
The solution is the placement of the pieces on the board as a jpeg image.

# Solver logic
clasic enumeration/backtracking algorithm.
The enumeration starts with the "larger" pices (4 squares) and leaves the smaller ones to the end of the enumeration.


# Architecture
FE - React
BE - Google App Engine (Python)

Similar to the ~/repos/tellem project

