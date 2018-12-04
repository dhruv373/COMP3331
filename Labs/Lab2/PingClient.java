import java.io.*;
import java.net.*;
import java.util.*;
import java.time.*;

/*
 * Server to process ping requests over UDP. 
 * The server sits in an infinite loop listening for incoming UDP packets. 
 * When a packet comes in, the server simply sends the encapsulated data back to the client.
 */

public class PingClient
{
   private static final double LOSS_RATE = 0.3;
   private static final int AVERAGE_DELAY = 100;  // milliseconds

   public static void main(String[] args) throws Exception
   {
      // Get command line argument.
      if (args.length != 2) {
         System.out.println("Required arguments in format: host port");
         return;
      }
      int port = Integer.parseInt(args[1]);
      String serverName = args[0];
      System.out.println(port);
      // Create random number generator for use in simulating 
      // packet loss and network delay.
      Random random = new Random();

      // Create a datagram socket for receiving and sending UDP packets
      // through the port specified on the command line.
      DatagramSocket socket = new DatagramSocket();
      
      //Pass in local host 127.0.0.1
      InetAddress ip = InetAddress.getByName(serverName);
      ArrayList<Long> rtt_array = new ArrayList<Long>(10);
      //ping the server 10 times by sending text msg increments of i
      for(int i =0; i < 10; i++){
          LocalTime time = LocalTime.now();	 

          String Message = "Ping "+ i + " " + time + "\r" +"\n";	    
	      DatagramPacket request = new DatagramPacket(Message.getBytes(), Message.length(), ip , port);
        
	    
          long sentTime = System.currentTimeMillis();
          
          socket.send(request);
	      DatagramPacket reply = new DatagramPacket(new byte[1024], 1024);

	      socket.setSoTimeout(1000);

	      try{
             // wait either for the reply from the server
		     socket.receive(reply);
             long receivedTime = System.currentTimeMillis();
             //System.out.println(receivedTime);
             long rtt = receivedTime - sentTime;
             rtt_array.add(rtt);
             System.out.println("ping to 127.0.0.1 , seq = " + i + ", rtt = " +  rtt + "ms\n");
	      }catch(IOException E){
             //timeout before transmitting the next ping
		     System.out.println("Packets dropped\n");
	      }
      }

      long sum = 0;
      for(int i =0; i < rtt_array.size(); i++){
         sum += rtt_array.get(i);    
      }

      System.out.println("Average rtt = " + sum/10 + "\n" + "Maximum rtt = " + Collections.max(rtt_array) + "\n" + "Minimum rtt = " + Collections.min(rtt_array) + "\n");
 
   }

   /* 
    * Print ping data to the standard output stream.
    */
   private static void printData(DatagramPacket request) throws Exception
   {
      // Obtain references to the packet's array of bytes.
      byte[] buf = request.getData();

      // Wrap the bytes in a byte array input stream,
      // so that you can read the data as a stream of bytes.
      ByteArrayInputStream bais = new ByteArrayInputStream(buf);

      // Wrap the byte array output stream in an input stream reader,
      // so you can read the data as a stream of characters.
      InputStreamReader isr = new InputStreamReader(bais);

      // Wrap the input stream reader in a bufferred reader,
      // so you can read the character data a line at a time.
      // (A line is a sequence of chars terminated by any combination of \r and \n.) 
      BufferedReader br = new BufferedReader(isr);

      // The message data is contained in a single line, so read this line.
      String line = br.readLine();

      // Print host address and data received from it.
      System.out.println(
         "Received from " + 
         request.getAddress().getHostAddress() + 
         ": " +
         new String(line) );
   }
}
