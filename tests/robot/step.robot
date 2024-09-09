*** Settings ***
Library  DebugLibrary

** test cases **
test1
    debug
    log to console  working
    @{list} =  Create List    hello    world

test2
    log to console  another test case
    log to console  end
