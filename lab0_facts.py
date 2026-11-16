"""
Fixed facts about Lab0 itself (the sender), kept in one place.

These are NOT things that need to be found in a prospect's search
results -- they're true regardless of which company the email is about.
The grounding checker needs this list so it doesn't flag Lab0's own
standard value-prop language (e.g. "Lab0 compresses implementation
cycles from months to days") as an unsupported claim about the
PROSPECT -- that was a false-positive bug in the first version of the
grounding check, which only knew the prospect's intel and treated any
sentence describing Lab0's own product as unverifiable.
"""

LAB0_FACTS = (
    "Lab0 builds AI agents that cut enterprise software implementation time "
    "from months to days. The agents handle discovery, planning, "
    "configuration, testing, and change requests for SAP, Salesforce, "
    "NetSuite, D365, ServiceNow, and Workday implementations. This is "
    "Lab0's own fixed product description -- it is always true and does not "
    "need to be supported by a prospect's search results."
)
