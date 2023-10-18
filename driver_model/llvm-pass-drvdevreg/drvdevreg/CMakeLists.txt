add_library(DrvDevRegPass MODULE
    DrvDevReg.cpp
)

target_compile_features(DrvDevRegPass PRIVATE cxx_range_for cxx_auto_type)

set_target_properties(DrvDevRegPass PROPERTIES
    COMPILE_FLAGS "-fno-rtti"
)

if(APPLE)
    set_target_properties(DrvDevRegPass PROPERTIES
        LINK_FLAGS "-undefined dynamic_lookup"
    )
endif(APPLE)
