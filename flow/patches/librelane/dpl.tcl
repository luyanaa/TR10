# Copyright 2020-2022 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb

source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl

# TR10: design-specific hook that re-inserts cells the stock DPL removed
# (`common/dpl.tcl` starts with `remove_fillers`).  examples/c4004_cmp uses
# it to put the upstream FILL3/FILL2 cells back at their exact coordinates
# after legalisation, so detailed placement can work on an empty-site
# floorplan while the routed GDS still carries the upstream well geometry.
# It runs before the final check_placement, so the re-inserted cells are
# validated too.
if { [info exists ::env(DESIGN_DIR)] && [file exists $::env(DESIGN_DIR)/post_dpl.tcl] } {
    puts "\[INFO\] TR10: sourcing post-DPL hook $::env(DESIGN_DIR)/post_dpl.tcl"
    source $::env(DESIGN_DIR)/post_dpl.tcl
}

check_placement -verbose

write_views

report_design_area_metrics
