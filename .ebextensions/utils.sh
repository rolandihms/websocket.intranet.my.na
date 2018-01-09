#!/usr/bin/env bash
set -e

SCRIPT_PATH=`dirname $0`

# An error exit function
error_exit() {
    echo "$1" 1>&2
    exit 1
}

# Copy + chmod + chown
# copy_ext source target 0755 user:group
copy_ext() {
    #cp + chmod + chown
    local source=$1
    local target=$2
    local permission=$3
    local user=$4
    local group=$5
    if ! cp $source $target; then
        error_exit "Can not copy ${source} to ${target}"
    fi
    if ! chmod -R $permission $target; then
        error_exit "Can not do chmod ${permission} for ${target}"
    fi
    if ! chown $user:$group $target; then
        error_exit "Can not do chown ${user}:${group} for ${target}"
    fi
    echo "cp_ext: ${source} -> ${target} chmod ${permission} & chown ${user}:${group}"
}

is_leader() {
    # Check for leader: /opt/elasticbeanstalk/bin/leader-test.sh:
    # use as
    # if is_leader; then
    #    dosmth
    # else
    #    doelse
    # fi
    if [[ "$EB_IS_COMMAND_LEADER" == "true" ]]; then
        # to be used in if's, so '0' means true (like for script exit code - 0 is success)
        #return 0
        #more clear (true returns 0)
        true
    else
        # to be used in if's, so '1' means false
        #return 1
        #more clear (false returns non zero)
        false
    fi
}

script_add_line() {
    local target_file=$1
    local check_text=$2
    local add_text=$3

    if grep -q "$check_text" "$target_file"
    then
        echo "Modification ${check_text} found in ${target_file}"
    else
        echo ${add_text} >> ${target_file}
        echo "Modification ${add_text} added to ${target_file}"
    fi
}