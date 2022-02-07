//
// Copyright © 2017 Arm Ltd. All rights reserved.
// SPDX-License-Identifier: MIT
//

#pragma once

#include <backendsCommon/WorkloadData.hpp>
#include <armnn/Tensor.hpp>

namespace armnn
{
void Concatenate(const ConcatQueueDescriptor &data,
                 std::vector<ITensorHandle*> inputs,
                 std::vector<ITensorHandle*> outputs);
} //namespace armnn
