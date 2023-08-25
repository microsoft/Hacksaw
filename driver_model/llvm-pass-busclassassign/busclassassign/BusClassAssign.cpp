// SPDX-License-Identifier: MIT
// Copyright (c) 2023, Microsoft Corporation.
#include "llvm/Pass.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Operator.h"
#include "llvm/IR/Constants.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#include "llvm/ADT/SmallString.h"
#include <vector>
#include <string>
#include <algorithm>

using namespace llvm;

namespace {
  std::vector<Value*> classStruct;
  std::vector<Value*> busTypeStruct;

  struct BusClassAssignPass : public ModulePass {
    static char ID;
    BusClassAssignPass() : ModulePass(ID) {}
    virtual bool runOnModule(Module &M) {
      Module *m = &M;
      for (Module::global_iterator i = m->global_begin(), e = m->global_end(); i != e; ++i) {
        GlobalVariable &GV = *i;
        if (GV.hasInitializer()) {
          if (auto *init = GV.getInitializer()) {
            if (init->getType()->isStructTy()) {
              if (init->getType()->getStructName().equals("struct.class"))
                classStruct.push_back(&GV);
              else if (init->getType()->getStructName().equals("struct.bus_type") ||
                  init->getType()->getStructName().equals("struct.xen_bus_type"))
                busTypeStruct.push_back(&GV);
            }
          }
        }
      }

      for (auto &F : M) {
        for (auto &BB : F) {
          for (auto &Inst : BB) {
            if (auto *ai = dyn_cast<AllocaInst>(&Inst)) {
              auto *typ = ai->getAllocatedType();
              if (ai->getType()->isStructTy()) {
                if (ai->getType()->getStructName().equals("struct.class"))
                  classStruct.push_back(&Inst);
                else if (ai->getType()->getStructName().equals("struct.bus_type") ||
                    ai->getType()->getStructName().equals("struct.xen_bus_type"))
                  busTypeStruct.push_back(&Inst);
              }
            }
          }
        }
      }

      for (auto &F : M) {
        for (auto &BB : F) {
          for (auto &Inst : BB) {
            if (auto *si = dyn_cast<StoreInst>(&Inst)) {
              if (std::find(classStruct.begin(), classStruct.end(), si->getValueOperand()) !=
                  classStruct.end()) {
                errs() << "class: " << si->getValueOperand()->getName() <<
                  " " << F.getName() << " " << M.getName() << "\n";
              }
              else if (std::find(busTypeStruct.begin(), busTypeStruct.end(), si->getValueOperand()) !=
                  busTypeStruct.end()) {
                errs() << "bus_type: " << si->getValueOperand()->getName() <<
                  " " << F.getName() << " " << M.getName() << "\n";
              }
            }
            else if (auto *gep = dyn_cast<GEPOperator>(&Inst)) {
              auto *typ = gep->getSourceElementType();
              if (!typ->isStructTy())
                continue;

              bool isClass = false, isBus = false;
              if (typ->getStructName().equals("struct.class"))
                isClass = true;
              else if (typ->getStructName().equals("struct.bus_type") ||
                  typ->getStructName().equals("struct.xen_bus_type"))
                isBus = true;
              else
                continue;

              bool isStore = false;
              for (auto u : gep->users()) {
                if (auto *si = dyn_cast<StoreInst>(u)) {
                  if (si->getValueOperand() == gep) {
                    isStore = true;
                    break;
                  }
                }
              }

              if (isStore) {
                if (isClass)
                  errs() << "class: ??? " << F.getName() << " " << M.getName() << "\n";
                else
                  errs() << "bus_type: ??? " << F.getName() << " " << M.getName() << "\n";
              }
            }
          }
        }
      }
      return false;
    }
  };
}

char BusClassAssignPass::ID = 0;
static RegisterPass<BusClassAssignPass> X("busclassassign", "Bus/Class Assignment Detector Pass", false, false);
