*** Settings ***
Library  DebugLibrary

Suite Setup    Setup


*** Keywords ***
Setup
    debug
    log to console  __init__ working
    @{list} =  Create List    __init__    hello    world
