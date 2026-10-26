# TR10 PDK setup sourced by LibreLane Magic steps.
if {[tech name] != "TR10"} {
    tech load [file join [file dirname [file normalize [info script]]] TR10.tech]
}
