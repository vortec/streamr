# Copyright (C) 2015 Richard Klees <richard.klees@rwth-aachen.de>

"""
# Rationales

A streaming pipeline is build from three different kind of objects:

* Producers send data downstream
* Consumers receive data from upstream
* Pipes receive data from upstream, transform it and send it downstream.

Depending on their types the object have to be able to tell which type of data
they receive and send. This is to make construction of valid streaming pipelines
fault resistant, thus having to do less error handling when actually processing
data through a pipeline.

Elements of a stream can be combined vertically by using the shift operators 
>> and <<. 

It should be possible to process the same pipeline multiple times and even in
parallel, without the different process interfering with each other.
"""

class StreamPart(object):
    """
    Common base class for the parts of a stream processing pipeline.
    """
    def __rshift__(self, other):
        """
        Compose two parts to get a new part.

        __rshift__ is left biased, this a >> b >> c = (a >> b) >> c
        """
        return compose_stream_parts(self, other)

    def __lshift__ (self, other):
        """
        Compose two part to get a new part.
        """
        return compose_stream_parts(other, self)

    def get_initial_state(self):
        """
        Should return a state object that is used to pass state during one
        execution of the stream part.

        The state object could e.g. be used to hold references to resources.
        """
        raise NotImplementedError("StreamPart::get_initial_state: implement me!")

    def shutdown_state(self, state):
        """
        Shut perform appropriate shutdown actions for the given state. Will be
        called after one execution of the pipeline with the resulting state.
        """
        raise NotImplementedError("StreamPart::shutdown_state: implement me!")
    

class Producer(StreamPart):
    """
    A producer is the source for a stream, that is, it produces new data for
    the downstream.
    """
    def type_out(self):
        """
        Get the type of output this producer produces.
        """
        raise NotImplementedError("Producer::type_out: implement me!")

    def __str__(self):
        return "(() -> %s)" % self.type_out()

class Consumer(StreamPart):
    """
    A consumer is the sink for a stream, that is it consumes data from upstream
    without producing new values.
    """
    def type_in(self):
        """
        Get the type, this consumer consumes.
        """
        raise NotImplementedError("Consumer::type_in: implement me!")

    def __str__(self):
        return "(%s -> ())" % self.type_in()

class Pipe(Producer, Consumer):
    """
    A pipe is an element between a source and a sink, that is it consumes data
    from upstream an produces new data for downstream.
    """ 
    def __str__(self):
        return "(%s -> %s)" % (self.type_in(), self.type_out()) 

class StreamProcess(object):
    """
    A stream process is a completely defined process between sources and sinks
    with no dangling ends. It could be run.
    """
    def run(self):
        """
        Let this stream process run.
        """
        pass

# Objects from the classes need to respect the follwing rules, where abbreaviations
# for the names are used
#
# any >> Pr = error
# Co >> any = error
# Pi >> Pi = Pi
# SP >> any = error
# any >> SP = error
# Pr >> Pi = Pr
# Pi >> Co = Co
# Pr >> Co = SP

def compose_stream_parts(left, right):
    """ 
    Compose two stream parts to get a new one.
    
    Throws TypeErrors when parts can't be combined.
    """
    t_left = type(left)
    t_right = type(right)

    if t_left == Pipe and t_right == Pipe:
        return FusePipes(left, right)
    elif t_left == Pipe and t_right == Consumer:
        return PrependPipe(left, right)
    elif t_left == Producer and t_right == Pipe:
        return AppendPipe(left, right)
    elif t_left == Producer and t_right == Consumer:
        raise NotImplementedError("compose_stream_parts: implement fusion of "
                                  "producer and consumer to stream process.")
    else:
        raise TypeError("Can't compose %s and %s" % (left, right))


class ComposedStreamPart(object):
    """
    Mixin for all composed stream parts.
    """
    def __init__(self, left, right):
        if left.type_out() != right.type_in():
            raise TypeError("Can't compose %s and %s" % (left, right))

        self.left = left
        self.right = right
    

class FusePipe(Pipe, ComposedStreamPart):
    """
    A pipe build from two other pipes.
    """
    def type_in(self):
        return self.left.type_in()

    def type_out(self):
        return self.right.type_out()

class PrependPipe(Consumer, ComposedStreamPart):
    """
    A consumer build from another consumer with a prepended pipe.
    """
    def type_in(self):
        return self.left.type_in()
        
class AppendPipe(Producer, ComposedStreamPart):
    """
    A producer build from another producer with an appended pipe.
    """
    def type_out(self):
        return self.right.type_out()
