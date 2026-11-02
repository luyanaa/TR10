# TR10 Netgen setup — intentionally not a functional LVS deck.
#
# The supported TR10 LVS backend is the KLayout runset
# (libs.tech/klayout/tech/lvs/run.lvs plus run_mask_stdcell.lvs for the
# post-MDP Mask view).  No device classes, model mapping, or hierarchical
# compare rules have been qualified for Netgen, so this file fails loudly
# instead of silently pretending Netgen LVS is signed off.
puts stderr "ERROR: TR10 Netgen LVS setup is not configured."
puts stderr "       Use the KLayout LVS runset (libs.tech/klayout/tech/lvs/run.lvs) instead."
error "TR10 Netgen LVS is not supported; use KLayout LVS"
