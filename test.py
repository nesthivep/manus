import asyncio
import os
import sys
import time
from typing import Dict, Any, List, Optional

# Add the app directory to the path if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tool.instagram import InstagramTool
from app.tool.base import ToolResult

class InstagramTester:
    """Test harness for Instagram tool functionality"""
    
    def __init__(self):
        self.tool = InstagramTool()
        self.test_results = []
        self.test_image_path = os.environ.get("TEST_IMAGE_PATH", "./test_image.jpg")
        self.test_video_path = os.environ.get("TEST_VIDEO_PATH", "./test_video.mp4")
        self.test_username = os.environ.get("TEST_TARGET_USERNAME", "instagram")
        self.saved_post_id = None
        
    async def run_all_tests(self):
        """Run all test functions and report results"""
        print("\n=== INSTAGRAM TOOL TEST SUITE ===\n")
        
        # Core functionality tests
        await self.test_initialization()
        
        # User management tests
        await self.test_search_users()
        await self.test_get_user_info()
        await self.test_follow_unfollow()
        await self.test_get_followers()
        await self.test_get_following()
        
        # Content tests (if test media is available)
        if os.path.exists(self.test_image_path):
            await self.test_create_post()
            if self.saved_post_id:
                await self.test_get_insights()
                await self.test_delete_post()
        else:
            print(f"⚠️ Skipping post tests - test image not found at {self.test_image_path}")
        
        # Story test (if test media is available)
        if os.path.exists(self.test_image_path):
            await self.test_create_story()
        
        # Feed and discovery tests
        await self.test_get_user_feed()
        await self.test_get_location_posts()
        
        # Print summary
        self.print_summary()
    
    async def test_initialization(self):
        """Test that the tool initializes and logs in properly"""
        try:
            start_time = time.time()
            if hasattr(self.tool.client, 'user_id') and self.tool.client.user_id:
                logged_in_user = self.tool.client.username
                self.record_result("initialization", True, f"Successfully initialized and logged in as {logged_in_user}")
            else:
                self.record_result("initialization", False, "Failed to initialize or log in")
            print(f"Initialization test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("initialization", False, f"Error during initialization: {str(e)}")
    
    async def test_search_users(self):
        """Test searching for users"""
        try:
            start_time = time.time()
            result = await self.tool.execute(action="search_users", query="instagram")
            if result.error:
                self.record_result("search_users", False, f"Error: {result.error}")
            else:
                users_found = len(result.data.get("users", []))
                self.record_result("search_users", users_found > 0, 
                                  f"Found {users_found} users matching 'instagram'")
            print(f"Search users test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("search_users", False, f"Exception: {str(e)}")
    
    async def test_get_user_info(self):
        """Test getting user info by username"""
        try:
            start_time = time.time()
            # First try direct method
            result = await self.tool.execute(action="get_user_feed", username=self.test_username, limit=1)
            
            if result.error:
                # If direct method fails, try search first
                search_result = await self.tool.execute(action="search_users", query=self.test_username, limit=1)
                if search_result.error or not search_result.data.get("users"):
                    self.record_result("get_user_info", False, f"Could not find test user {self.test_username}")
                    return
                    
                user_id = search_result.data["users"][0]["user_id"]
                result = await self.tool.execute(action="get_user_feed", user_id=user_id, limit=1)
            
            if result.error:
                self.record_result("get_user_info", False, f"Error: {result.error}")
            else:
                self.record_result("get_user_info", True, f"Successfully retrieved info for user {self.test_username}")
            print(f"Get user info test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("get_user_info", False, f"Exception: {str(e)}")
            
    async def test_follow_unfollow(self):
        """Test following and unfollowing a user"""
        try:
            start_time = time.time()
            # Follow
            follow_result = await self.tool.execute(action="follow_user", username=self.test_username)
            follow_success = not follow_result.error
            
            if follow_success:
                self.record_result("follow_user", True, f"Successfully followed {self.test_username}")
                
                # Wait a moment before unfollowing
                await asyncio.sleep(2)
                
                # Unfollow
                unfollow_result = await self.tool.execute(action="unfollow_user", username=self.test_username)
                unfollow_success = not unfollow_result.error
                
                if unfollow_success:
                    self.record_result("unfollow_user", True, f"Successfully unfollowed {self.test_username}")
                else:
                    self.record_result("unfollow_user", False, f"Error unfollowing: {unfollow_result.error}")
            else:
                self.record_result("follow_user", False, f"Error following: {follow_result.error}")
                self.record_result("unfollow_user", False, "Skipped (follow failed)")
                
            print(f"Follow/unfollow test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("follow_unfollow", False, f"Exception: {str(e)}")
    
    async def test_get_followers(self):
        """Test getting followers list"""
        try:
            start_time = time.time()
            result = await self.tool.execute(action="get_followers", username=self.test_username, limit=5)
            
            if result.error:
                self.record_result("get_followers", False, f"Error: {result.error}")
            else:
                followers = result.data.get("followers", [])
                self.record_result("get_followers", len(followers) > 0, 
                                  f"Retrieved {len(followers)} followers for {self.test_username}")
            print(f"Get followers test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("get_followers", False, f"Exception: {str(e)}")
    
    async def test_get_following(self):
        """Test getting following list"""
        try:
            start_time = time.time()
            # Use the authenticated user's username
            username = self.tool.client.username
            result = await self.tool.execute(action="get_following", username=username, limit=5)
            
            if result.error:
                self.record_result("get_following", False, f"Error: {result.error}")
            else:
                following = result.data.get("following", [])
                self.record_result("get_following", True, 
                                  f"Retrieved {len(following)} accounts that {username} is following")
            print(f"Get following test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("get_following", False, f"Exception: {str(e)}")
    
    async def test_create_post(self):
        """Test creating a post with an image"""
        try:
            start_time = time.time()
            caption = f"Test post from Instagram Tool Tester - {time.strftime('%Y-%m-%d %H:%M:%S')}"
            result = await self.tool.execute(
                action="create_post", 
                caption=caption,
                image_path=self.test_image_path
            )
            
            if result.error:
                self.record_result("create_post", False, f"Error: {result.error}")
            else:
                self.saved_post_id = result.data.get("post_id")
                post_url = result.data.get("post_url")
                self.record_result("create_post", True, f"Successfully created post: {post_url}")
            print(f"Create post test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("create_post", False, f"Exception: {str(e)}")
    
    async def test_get_insights(self):
        """Test getting insights for a post"""
        if not self.saved_post_id:
            self.record_result("get_insights", False, "Skipped (no post_id available)")
            return
            
        try:
            start_time = time.time()
            result = await self.tool.execute(action="get_insights", post_id=self.saved_post_id)
            
            if result.error:
                self.record_result("get_insights", False, f"Error: {result.error}")
            else:
                self.record_result("get_insights", True, f"Successfully retrieved insights for post")
            print(f"Get insights test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("get_insights", False, f"Exception: {str(e)}")
    
    async def test_delete_post(self):
        """Test deleting a post"""
        if not self.saved_post_id:
            self.record_result("delete_post", False, "Skipped (no post_id available)")
            return
            
        try:
            start_time = time.time()
            result = await self.tool.execute(action="delete_post", post_id=self.saved_post_id)
            
            if result.error:
                self.record_result("delete_post", False, f"Error: {result.error}")
            else:
                self.record_result("delete_post", True, f"Successfully deleted post {self.saved_post_id}")
            print(f"Delete post test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("delete_post", False, f"Exception: {str(e)}")
    
    async def test_create_story(self):
        """Test creating a story"""
        try:
            start_time = time.time()
            result = await self.tool.execute(
                action="create_story", 
                image_path=self.test_image_path,
                caption="Test story from tool tester"
            )
            
            if result.error:
                self.record_result("create_story", False, f"Error: {result.error}")
            else:
                story_id = result.data.get("story_id")
                self.record_result("create_story", True, f"Successfully created story with ID {story_id}")
            print(f"Create story test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("create_story", False, f"Exception: {str(e)}")
    
    async def test_get_user_feed(self):
        """Test getting a user's feed"""
        try:
            start_time = time.time()
            result = await self.tool.execute(
                action="get_user_feed", 
                username=self.test_username,
                limit=5
            )
            
            if result.error:
                self.record_result("get_user_feed", False, f"Error: {result.error}")
            else:
                posts = result.data.get("posts", [])
                self.record_result("get_user_feed", len(posts) > 0, 
                                  f"Retrieved {len(posts)} posts from {self.test_username}'s feed")
            print(f"Get user feed test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("get_user_feed", False, f"Exception: {str(e)}")
    
    async def test_get_location_posts(self):
        """Test getting posts from a location (using Times Square location ID)"""
        try:
            start_time = time.time()
            # Times Square location ID
            location_id = "212988663"
            result = await self.tool.execute(
                action="get_location_posts", 
                location_id=location_id,
                limit=5
            )
            
            if result.error:
                self.record_result("get_location_posts", False, f"Error: {result.error}")
            else:
                posts = result.data.get("posts", [])
                self.record_result("get_location_posts", len(posts) > 0, 
                                  f"Retrieved {len(posts)} posts from location ID {location_id}")
            print(f"Get location posts test completed in {time.time() - start_time:.2f}s")
        except Exception as e:
            self.record_result("get_location_posts", False, f"Exception: {str(e)}")
    
    def record_result(self, test_name: str, success: bool, message: str):
        """Record a test result with details"""
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "message": message
        })
        
        # Print immediate feedback
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
    
    def print_summary(self):
        """Print a summary of all test results"""
        success_count = sum(1 for result in self.test_results if result["success"])
        total_count = len(self.test_results)
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        
        print("\n=== TEST SUMMARY ===")
        print(f"Passed: {success_count}/{total_count} ({success_rate:.1f}%)")
        
        if success_count == total_count:
            print("\n✅ All tests passed! Instagram tool is working correctly.")
        else:
            print("\n⚠️ Some tests failed. Check the details above for errors.")
            
            # Print failed tests for quick reference
            print("\nFailed tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"❌ {result['test_name']}: {result['message']}")


async def main():
    tester = InstagramTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    # Make sure test image exists
    test_image_path = os.environ.get("TEST_IMAGE_PATH", "./image.jpg")
    if not os.path.exists(test_image_path):
        print(f"⚠️ Warning: Test image not found at {test_image_path}")
        print("Some tests will be skipped. Create an image at this path or set TEST_IMAGE_PATH environment variable.")
    
    asyncio.run(main())
