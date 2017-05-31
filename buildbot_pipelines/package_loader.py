"""load packages from pypi if they are not already loaded
Intended to be run from out-of-mainloop threads.

Need to be threadsafe, as there is a strong possibility to have several builds starting at the same time
"""


def import_package(package):
    #  @TODO
    return {}
