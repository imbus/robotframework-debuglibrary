*** Settings ***
Library    DateTime

*** Keywords ***

My Keyword
    ${date}=    Get Current Date
    Log To Console    ${date}